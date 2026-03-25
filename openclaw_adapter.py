"""
OpenClaw 集成适配器
自动管理三层记忆，防128k溢出
支持按session_id多会话隔离，每消息自动固化
"""
import hashlib
from datetime import datetime
from core.eternal_layer import EternalLayer
from core.impression_layer import ImpressionLayer
from core.working_memory import WorkingMemory

# 全局实例字典：按session_id隔离记忆系统
_memory_systems = {}

class OpenClawAdapter:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        # 每个会话独立的存储路径
        base_path = f"~/.bio-memory/sessions/{session_id}/eternal"
        db_path = f"~/.bio-memory/sessions/{session_id}/impressions.db"
        
        self.eternal = EternalLayer(base_path=base_path)
        self.impression = ImpressionLayer(db_path=db_path)
        self.working = WorkingMemory(max_tokens=100000)
        
        # 设置驱逐回调：工作记忆满时自动转印象层
        self.working.on_evict(self._handle_eviction)
        # 自动固化阈值：每收到3条消息自动固化一次
        self.auto_consolidate_threshold = 3
        self.message_count = 0
    
    def _handle_eviction(self, chunk):
        """自动将工作记忆驱逐到印象层"""
        pointer = self.eternal.store(chunk.content, {
            "type": "evicted_memory",
            "role": chunk.role,
            "session_id": self.session_id
        })
        self.impression.create(chunk.content, pointer)
        print(f"[Bio-Memory] 会话{self.session_id} 已固化驱逐内容: {pointer[:60]}...")
    
    def _consolidate_current(self):
        """固化当前工作记忆中最新的一条消息到永恒层"""
        if len(self.working.chunks) == 0:
            return
        
        latest_chunk = self.working.chunks[-1]
        # 避免重复固化：检查内容哈希
        content_hash = hashlib.sha256(latest_chunk.content.encode()).hexdigest()[:16]
        cache_key = f"consolidated_{content_hash}"
        
        if not hasattr(self, cache_key):
            pointer = self.eternal.store(latest_chunk.content, {
                "type": "message",
                "role": latest_chunk.role,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat()
            })
            self.impression.create(latest_chunk.content, pointer)
            setattr(self, cache_key, True)
    
    def process_message(self, role: str, content: str) -> list:
        """
        处理每条消息，自动防溢出 + 自动固化
        返回: 当前上下文（已压缩）
        """
        # 添加到工作记忆（自动驱逐旧的）
        self.working.add(role, content)
        
        # 每处理一条消息，自动固化最新内容
        self.message_count += 1
        if self.message_count % self.auto_consolidate_threshold == 0:
            self._consolidate_current()
        
        # 如果用户提到过去，主动回忆
        if any(word in content for word in ["记得", "之前", "大概", "以前", "上次", "之前我们"]):
            return self._augment_with_recall(content)
        
        return self.working.get_context()
    
    def force_consolidate(self):
        """强制固化当前所有工作记忆内容到永恒层"""
        for chunk in self.working.chunks:
            pointer = self.eternal.store(chunk.content, {
                "type": "manual_consolidate",
                "role": chunk.role,
                "session_id": self.session_id
            })
            self.impression.create(chunk.content, pointer)
        print(f"[Bio-Memory] 会话{self.session_id} 强制固化完成: {len(self.working.chunks)}条")
    
    def _augment_with_recall(self, query: str) -> list:
        """主动回忆并注入上下文"""
        memories = self.impression.recall_fuzzy(query, top_k=2)
        
        for mem in memories:
            if mem.get('confidence', 0) > 0.6:
                try:
                    content = self.eternal.retrieve(mem['pointer'])
                    # 作为 system 消息注入
                    self.working.add("system", f"[相关记忆] {mem['gist']}\n{content[:1000]}")
                except Exception as e:
                    print(f"[Bio-Memory] 加载记忆失败: {e}")
        
        return self.working.get_context()
    
    def store_important(self, content: str, metadata: dict = None):
        """显式存储重要信息到永恒层"""
        meta = metadata or {}
        meta["session_id"] = self.session_id
        pointer = self.eternal.store(content, meta)
        self.impression.create(content, pointer, meta)
        return pointer


def get_memory_system(session_id: str = "default") -> OpenClawAdapter:
    """
    获取或创建指定session的记忆系统实例
    不同session_id完全隔离，不会串记忆
    """
    global _memory_systems
    if session_id not in _memory_systems:
        _memory_systems[session_id] = OpenClawAdapter(session_id=session_id)
    return _memory_systems[session_id]

def cleanup_session(session_id: str):
    """清理指定会话的内存记忆，保留磁盘存储"""
    global _memory_systems
    if session_id in _memory_systems:
        del _memory_systems[session_id]

# OpenClaw Hook 绑定示例
def on_message_hook(session_id: str, role: str, content: str):
    """
    OpenClaw on_message 钩子，每收到/发送一条消息自动调用
    直接在OpenClaw配置中绑定这个函数即可
    """
    memory = get_memory_system(session_id)
    context = memory.process_message(role, content)
    # 返回压缩后的安全上下文，直接传给LLM
    return context

def on_session_end_hook(session_id: str):
    """会话结束钩子，强制固化所有内容"""
    if session_id in _memory_systems:
        memory = get_memory_system(session_id)
        memory.force_consolidate()
        cleanup_session(session_id)
