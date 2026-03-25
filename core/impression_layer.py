import hashlib
import sqlite3
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

class ImpressionLayer:
    """模糊记忆层 - 情绪+时间+实体索引"""
    def __init__(self, db_path: str = "~/.bio-memory/impressions.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()
    
    def _init_db(self):
        """初始化表结构"""
        # 开启WAL模式，解决读写锁冲突
        self.conn.execute("PRAGMA journal_mode=WAL;")
        
        # 基础印象表：用自增ID作为主键，兼容FTS的rowid整数要求
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS impressions (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                impression_id TEXT UNIQUE,  -- 原字符串ID作为唯一字段
                timestamp TEXT,
                time_fuzzy TEXT,
                emotion_vector TEXT,
                entities TEXT,
                gist TEXT,
                pointer TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                content_text TEXT  -- 原始内容片段，用于FTS搜索
            )
        """)
        
        # FTS5全文搜索虚拟表：绑定自增rowid
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS impression_fts 
            USING fts5(content_text, content='impressions', content_rowid='rowid')
        """)
        
        # 触发器：自动同步内容到FTS表
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS impression_after_insert
            AFTER INSERT ON impressions BEGIN
                INSERT INTO impression_fts(rowid, content_text)
                VALUES (new.rowid, new.content_text);
            END
        """)
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS impression_after_update
            AFTER UPDATE ON impressions BEGIN
                UPDATE impression_fts 
                SET content_text = new.content_text
                WHERE rowid = old.rowid;
            END
        """)
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS impression_after_delete
            AFTER DELETE ON impressions BEGIN
                DELETE FROM impression_fts WHERE rowid = old.rowid;
            END
        """)
        
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON impressions(timestamp)")
        self.conn.commit()
    
    def create(self, content: str, pointer: str, metadata: Dict = None) -> str:
        """从内容创建印象（有损压缩）"""
        meta = metadata or {}
        
        # 简单实体提取
        entities = self._extract_entities(content)
        
        # 简单情绪检测
        emotion = self._detect_emotion(content)
        
        # 生成 gist
        gist = content[:100].replace('\n', ' ') + "..."
        
        impression_id = hashlib.md5(f"{pointer}{datetime.now()}".encode()).hexdigest()[:16]
        
        # 保存前1000字符作为全文搜索内容
        content_text = content[:1000].replace('\n', ' ')
        
        # 插入数据：rowid自动生成
        self.conn.execute("""
            INSERT INTO impressions (impression_id, timestamp, time_fuzzy, emotion_vector, entities, gist, pointer, content_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            impression_id,
            datetime.now().isoformat(),
            "recent",
            json.dumps(emotion),
            json.dumps(entities),
            gist,
            pointer,
            content_text
        ))
        self.conn.commit()
        return impression_id
    
    def recall_fuzzy(self, query: str, top_k: int = 5) -> List[Dict]:
        """模糊回忆 - 支持'大概上个月关于OpenClaw的讨论'"""
        query_lower = query.lower()
        
        # 时间解析
        time_filter = self._parse_time_query(query_lower)
        
        # 构建SQL：优先FTS全文搜索，再过滤时间
        sql = """
            SELECT i.impression_id, i.timestamp, i.gist, i.pointer, rank FROM impressions i
            JOIN impression_fts fts ON i.rowid = fts.rowid
            WHERE impression_fts MATCH ?
        """
        params = [query_lower]
        
        if time_filter:
            sql += " AND i.timestamp > ?"
            params.append(time_filter)
        
        sql += " ORDER BY rank, i.access_count DESC, i.timestamp DESC LIMIT ?"
        params.append(top_k)
        
        try:
            cursor = self.conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                # rank越小匹配度越高，转成置信度0-1
                confidence = max(0, 1 - (row[-1] / 10)) if row[-1] < 10 else 0.1
                results.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "gist": row[2],
                    "pointer": row[3],
                    "confidence": confidence
                })
                # 更新访问计数
                self.conn.execute(
                    "UPDATE impressions SET access_count = access_count + 1, last_accessed = ? WHERE impression_id = ?",
                    (datetime.now().isoformat(), row[0])
                )
            self.conn.commit()
            
            # 如果FTS没有结果，回退到实体匹配
            if not results:
                return self._fallback_recall(query_lower, time_filter, top_k)
                
            return results
            
        except Exception as e:
            # FTS搜索出错，回退到旧方法
            return self._fallback_recall(query_lower, time_filter, top_k)
    
    def _fallback_recall(self, query_lower: str, time_filter: str = None, top_k: int = 5) -> List[Dict]:
        """回退检索方法：实体关键词匹配"""
        sql = "SELECT impression_id, timestamp, gist, pointer FROM impressions WHERE 1=1"
        params = []
        
        if time_filter:
            sql += " AND timestamp > ?"
            params.append(time_filter)
        
        # 简单关键词匹配
        sql += " AND (gist LIKE ? OR entities LIKE ? OR content_text LIKE ?)"
        params.extend([f"%{query_lower[:30]}%", f"%{query_lower[:30]}%", f"%{query_lower[:30]}%"])
        
        sql += " ORDER BY access_count DESC, timestamp DESC LIMIT ?"
        params.append(top_k)
        
        cursor = self.conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "timestamp": row[1],
                "gist": row[2],
                "pointer": row[3],
                "confidence": 0.5
            })
            self.conn.execute(
                "UPDATE impressions SET access_count = access_count + 1, last_accessed = ? WHERE impression_id = ?",
                (datetime.now().isoformat(), row[0])
            )
        self.conn.commit()
        return results
    
    def _extract_entities(self, content: str) -> List[str]:
        """简单实体提取"""
        words = re.findall(r'\b[A-Z][a-zA-Z]*\b', content)
        return list(set(words))[:10]
    
    def _detect_emotion(self, content: str) -> Dict[str, float]:
        """简单情绪检测"""
        emotion_lexicon = {
            'anxiety': ['担心', '焦虑', '压力', 'overflow', '溢出', '错误', '失败'],
            'joy': ['成功', '解决', '棒', '优秀', '兴奋', '开心'],
            'determination': ['必须', '一定', '解决', '战胜', '克服']
        }
        
        scores = {}
        for emotion, keywords in emotion_lexicon.items():
            score = sum(1 for k in keywords if k in content) / max(len(keywords), 1)
            if score > 0:
                scores[emotion] = min(score, 1.0)
        
        return scores if scores else {"neutral": 1.0}
    
    def _parse_time_query(self, query: str) -> Optional[str]:
        """解析时间查询"""
        now = datetime.now()
        if "昨天" in query:
            return (now - timedelta(days=1)).isoformat()
        elif "上周" in query or "最近" in query:
            return (now - timedelta(days=7)).isoformat()
        elif "上个月" in query:
            return (now - timedelta(days=30)).isoformat()
        return None
