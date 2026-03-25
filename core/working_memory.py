import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class MemoryChunk:
    role: str  # user/assistant/system
    content: str
    timestamp: str
    hash: str

class WorkingMemory:
    """
    防溢出工作记忆 - 严格限制 4±1 chunks
    """
    def __init__(self, max_tokens: int = 100000, max_chunks: int = 5):
        self.max_tokens = max_tokens
        self.max_chunks = max_chunks
        self.chunks: List[MemoryChunk] = []
        self._evicted_callback = None
    
    def on_evict(self, callback):
        """设置驱逐回调（用于将内容转移到印象层）"""
        self._evicted_callback = callback
    
    def add(self, role: str, content: str) -> Optional[MemoryChunk]:
        """
        添加新内容，如果超出限制则驱逐最旧的
        返回：被驱逐的 chunk（如果有）
        """
        chunk = MemoryChunk(
            role=role,
            content=content,
            timestamp=hashlib.md5(content.encode()).hexdigest(),  # 简化为唯一ID
            hash=hashlib.sha256(content.encode()).hexdigest()[:16]
        )
        
        self.chunks.append(chunk)
        
        # 检查并清理
        evicted = None
        while len(self.chunks) > self.max_chunks or self._estimate_tokens() > self.max_tokens:
            evicted = self.chunks.pop(0)
            if self._evicted_callback:
                self._evicted_callback(evicted)
        
        return evicted
    
    def _estimate_tokens(self) -> int:
        """估算当前 token 数（中文 1 字 ≈ 1.2 tokens）"""
        total_chars = sum(len(c.content) for c in self.chunks)
        return int(total_chars * 1.2)
    
    def get_context(self) -> List[Dict]:
        """获取当前上下文（用于 LLM）"""
        return [{"role": c.role, "content": c.content} for c in self.chunks]
    
    def clear(self):
        """清空工作记忆"""
        self.chunks = []
    
    def deduplicate(self):
        """语义去重：移除与前面 80% 相似的内容"""
        if len(self.chunks) < 2:
            return
        
        unique = [self.chunks[0]]
        for chunk in self.chunks[1:]:
            if not self._is_similar(chunk, unique[-1]):
                unique.append(chunk)
        
        self.chunks = unique[-self.max_chunks:]  # 保持限制
    
    def _is_similar(self, a: MemoryChunk, b: MemoryChunk, threshold: float = 0.8) -> bool:
        """简单相似度检查（可替换为向量相似度）"""
        words_a = set(a.content[:100].split())  # 只比较前100字符
        words_b = set(b.content[:100].split())
        
        if not words_a:
            return False
        
        overlap = len(words_a & words_b) / len(words_a)
        return overlap > threshold
