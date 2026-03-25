"""
OpenClaw 集成适配器
自动管理三层记忆，防128k溢出
"""
from core.eternal_layer import EternalLayer
from core.impression_layer import ImpressionLayer
from core.working_memory import WorkingMemory

class OpenClawAdapter:
    def __init__(self):
        self.eternal = EternalLayer()
        self.impression = ImpressionLayer()
        self.working = WorkingMemory(max_tokens=100000)
        
        # 设置驱逐回调：工作记忆满时自动转印象层
        self.working.on_evict(self._handle_eviction)
    
    def _handle_eviction(self, chunk):
        """自动将工作记忆驱逐到印象层"""
        pointer = self.eternal.store(chunk.content, {
            "type": "evicted_memory",
            "role": chunk.role
        })
        self.impression.create(chunk.content, pointer)
        print(f"[Bio-Memory] 已固化到永恒层: {pointer}")
    
    def process_message(self, role: str, content: str) -> list:
        """
        处理每条消息，自动防溢出
        返回: 当前上下文（已压缩）
        """
        # 添加到工作记忆（自动驱逐旧的）
        self.working.add(role, content)
        
        # 如果用户提到过去，主动回忆
        if any(word in content for word in ["记得", "之前", "大概", "以前", "上次"]):
            return self._augment_with_recall(content)
        
        return self.working.get_context()
    
    def _augment_with_recall(self, query: str) -> list:
        """主动回忆并注入上下文"""
        memories = self.impression.recall_fuzzy(query, top_k=2)
        
        for mem in memories:
            if mem.get('confidence', 0) > 0.7:
                content = self.eternal.retrieve(mem['pointer'])
                # 作为 system 消息注入
                self.working.add("system", f"[相关记忆] {mem['gist']}\n{content[:1000]}")
        
        return self.working.get_context()
    
    def store_important(self, content: str, metadata: dict = None):
        """显式存储重要信息到永恒层"""
        meta = metadata or {}
        pointer = self.eternal.store(content, meta)
        self.impression.create(content, pointer, meta)
        return pointer


# 全局实例（OpenClaw 会话共享）
_memory_system = None

def get_memory_system() -> OpenClawAdapter:
    """获取或创建记忆系统实例"""
    global _memory_system
    if _memory_system is None:
        _memory_system = OpenClawAdapter()
    return _memory_system
