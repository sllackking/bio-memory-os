import sqlite3
import json
import re
import hashlib
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
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS impressions (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            time_fuzzy TEXT, -- '十年前', '上个月'
            emotion_vector TEXT, -- JSON: {"joy": 0.8, "anxiety": 0.2}
            entities TEXT, -- JSON: ["OpenClaw", "MSA"]
            gist TEXT, -- 一句话摘要
            pointer TEXT, -- 指向永恒层
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT
        )
        """)
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_time ON impressions(timestamp)
        """)
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_gist ON impressions(gist)
        """)
        self.conn.commit()
    
    def create(self, content: str, pointer: str, metadata: Dict = None) -> str:
        """
        从内容创建印象（有损压缩）
        """
        meta = metadata or {}
        
        # 简单实体提取（关键词）
        entities = self._extract_entities(content)
        
        # 简单情绪检测（词典法）
        emotion = self._detect_emotion(content)
        
        # 生成 gist（取前 100 字作为摘要）
        gist = content[:100].replace('\n', ' ') + "..."
        
        impression_id = hashlib.md5(f"{pointer}{datetime.now()}".encode()).hexdigest()[:16]
        
        self.conn.execute("""
        INSERT INTO impressions (id, timestamp, time_fuzzy, emotion_vector, entities, gist, pointer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            impression_id,
            datetime.now().isoformat(),
            "recent", # 可扩展为模糊时间解析
            json.dumps(emotion),
            json.dumps(entities),
            gist,
            pointer
        ))
        self.conn.commit()
        
        return impression_id
    
    def recall_fuzzy(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        模糊回忆
        支持："大概上个月关于 OpenClaw 的讨论"
        """
        # 解析查询
        query_lower = query.lower()
        
        # 时间解析（简化版）
        time_filter = self._parse_time_query(query_lower)
        
        # 实体提取（从查询中提取关键词）
        query_entities = [w for w in ["openclaw", "msa", "记忆", "代码", "qmd", "bmo", "bio-memory"] if w in query_lower]
        
        # 构建 SQL
        sql = "SELECT * FROM impressions WHERE 1=1"
        params = []
        
        if time_filter:
            sql += " AND timestamp > ?"
            params.append(time_filter)
        
        if query_entities:
            # 简单的全文搜索（生产环境可用 FTS5）
            entity_conditions = " OR ".join(["entities LIKE ?" for _ in query_entities])
            sql += f" AND ({entity_conditions})"
            params.extend([f"%{e}%" for e in query_entities])
        
        sql += " ORDER BY access_count DESC, timestamp DESC LIMIT ?"
        params.append(top_k)
        
        cursor = self.conn.execute(sql, params)
        results = []
        rows = cursor.fetchall()
        for row in rows:
            results.append({
                "id": row[0],
                "timestamp": row[1],
                "gist": row[5],
                "pointer": row[6],
                "confidence": 0.8 # 简化为固定值，可改为向量相似度
            })
        
        # 更新访问计数
        if rows:
            self.conn.execute(
                "UPDATE impressions SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                (datetime.now().isoformat(), rows[0][0])
            )
        
        self.conn.commit()
        return results
    
    def _extract_entities(self, content: str) -> List[str]:
        """简单实体提取（实际可用 NER）"""
        # 提取大写字母开头的词（专有名词）
        words = re.findall(r'\b[A-Z][a-zA-Z]*\b', content)
        return list(set(words))[:10] # 最多10个
    
    def _detect_emotion(self, content: str) -> Dict[str, float]:
        """简单情绪检测"""
        emotion_lexicon = {
            'anxiety': ['担心', '焦虑', '压力', 'overflow', '溢出', '错误', '失败'],
            'joy': ['成功', '解决', '棒', '优秀', '兴奋', '开心', '✅'],
            'determination': ['必须', '一定', '解决', '战胜', '克服']
        }
        
        scores = {}
        for emotion, keywords in emotion_lexicon.items():
            score = sum(1 for k in keywords if k in content) / max(len(keywords), 1)
            if score > 0:
                scores[emotion] = min(score, 1.0)
        
        return scores if scores else {"neutral": 1.0}
    
    def _parse_time_query(self, query: str) -> Optional[str]:
        """解析时间查询（简化）"""
        now = datetime.now()
        
        if "昨天" in query:
            return (now - timedelta(days=1)).isoformat()
        elif "上周" in query or "最近" in query:
            return (now - timedelta(days=7)).isoformat()
        elif "上个月" in query:
            return (now - timedelta(days=30)).isoformat()
        
        return None
