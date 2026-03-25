# Bio-Memory-OS

仿生记忆操作系统 - 分层记忆架构，解决 AI 长期陪伴的核心问题

## 核心特性

- **128k 溢出防护**: 严格工作记忆限制，永不出错
- **模糊回忆**: 支持"大概上周关于XXX的讨论"
- **十年可验证**: Git版本控制 + SHA-256校验，防篡改
- **格式永生**: Markdown + Git，比任何公司活得久

## 架构

```
Eternal Layer (Git)     → 永久存储，无损
Impression Layer (SQLite) → 模糊索引，情绪+时间+实体  
Working Memory (4±1 chunks) → 防溢出保护
```

## 快速开始

```python
from core.eternal_layer import EternalLayer
from core.impression_layer import ImpressionLayer
from core.working_memory import WorkingMemory

# 初始化三层记忆
eternal = EternalLayer()
impression = ImpressionLayer()
working = WorkingMemory(max_tokens=100000)

# 存储重要对话
pointer = eternal.store("重要内容", {
    "type": "conversation",
    "title": "关于记忆架构的讨论",
    "tags": ["bio-memory", "架构"]
})

# 创建印象（模糊索引）
impression.create("重要内容", pointer, {"entities": ["记忆", "架构"]})

# 模糊回忆
results = impression.recall_fuzzy("大概上周关于记忆架构的讨论")
```

## 对比现有方案

| 特性 | Claude-Mem | qmd | Bio-Memory-OS |
|------|-----------|-----|---------------|
| 128k防护 | ❌ | ❌ | ✅ |
| 十年可验证 | ❌ | ❌ | ✅ |
| 离线可用 | ⚠️ | ✅ | ✅ |
| 硬件要求 | A100 | 4GB RAM | 树莓派即可 |

## License

MIT - 自由使用，永不收费

---
**Timestamp**: 2026-03-25 22:47 UTC+8  
**Status**: 开发中 - 基础架构完成
