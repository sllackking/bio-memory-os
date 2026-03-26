from bio_memory_os.core.eternal_layer import EternalLayer
from bio_memory_os.core.impression_layer import ImpressionLayer
from bio_memory_os.core.working_memory import WorkingMemory

class OpenClawBMOAdapter:
    """BMO 记忆系统 OpenClaw 适配器"""
    def __init__(self):
        self.eternal = EternalLayer()
        self.impression = ImpressionLayer()
        self.working = WorkingMemory(max_tokens=100000)
        
        # 设置驱逐回调：工作记忆满时自动转印象层
        self.working.on_evict(self._handle_eviction)
        print("[BMO] 🧠 仿生记忆系统初始化完成")
    
    def _handle_eviction(self, chunk):
        """自动将工作记忆驱逐到印象层"""
        pointer = self.eternal.store(chunk.content, {
            "type": "evicted_memory",
            "role": chunk.role,
            "timestamp": chunk.timestamp
        })
        self.impression.create(chunk.content, pointer)
        print(f"[BMO] 💾 已固化记忆到永恒层: {pointer.split('/')[-1]}")
    
    def process_message(self, role: str, content: str) -> list:
        """
        处理每条消息，自动防溢出
        返回：当前上下文（已压缩）
        """
        # 添加到工作记忆（自动驱逐旧的）
        self.working.add(role, content)
        
        # 如果用户提到过去，主动回忆
        if any(word in content for word in ["记得", "之前", "大概", "以前", "回忆", "找一下", "上次"]):
            return self._augment_with_recall(content)
        
        return self.working.get_context()
    
    def _augment_with_recall(self, query: str) -> list:
        """主动回忆并注入上下文"""
        memories = self.impression.recall_fuzzy(query, top_k=2)
        
        # 加载最相关的到工作记忆（但保持总限制）
        for mem in memories:
            if mem['confidence'] > 0.7:
                content = self.eternal.retrieve(mem['pointer'])
                # 作为 system 消息注入
                self.working.add("system", f"""[BMO 相关记忆]
📅 时间: {mem['timestamp'].split('T')[0]}
📝 摘要: {mem['gist']}
📄 内容片段:
{content[:1500]}
---
""")
        
        return self.working.get_context()
    
    def store_memory(self, content: str, title: str = "untitled", tags: list = None) -> str:
        """手动存储重要记忆"""
        pointer = self.eternal.store(content, {
            "type": "manual_memory",
            "title": title,
            "tags": tags or []
        })
        self.impression.create(content, pointer, {"tags": tags})
        print(f"[BMO] ✅ 已手动保存记忆: {title}")
        return pointer
    
    def get_status(self) -> dict:
        """获取记忆系统状态"""
        return {
            "working_chunks": len(self.working.chunks),
            "working_tokens": self.working._estimate_tokens(),
            "eternal_path": str(self.eternal.base_path),
            "impression_db": str(self.impression.db_path)
        }

# 全局实例
bmo = OpenClawBMOAdapter()
