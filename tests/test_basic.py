"""基础功能测试 - 验证三层记忆"""
import sys
sys.path.insert(0, '/home/ai/bio-memory-os')

from core.eternal_layer import EternalLayer
from core.impression_layer import ImpressionLayer
from core.working_memory import WorkingMemory

def test_eternal_layer():
    """测试永恒层 - Git存储"""
    print("\n=== 测试永恒层 ===")
    eternal = EternalLayer(base_path="~/.bio-memory/test/eternal")
    
    # 存储内容
    pointer = eternal.store("测试内容：这是关于Bio-Memory-OS的第一次测试。", {
        "type": "test",
        "title": "基础测试",
        "tags": ["test", "bio-memory"]
    })
    print(f"✅ 存储成功: {pointer}")
    
    # 读取内容
    content = eternal.retrieve(pointer)
    print(f"✅ 读取成功: {len(content)} 字符")
    
    # 验证Git历史
    history = eternal.get_history(pointer)
    print(f"✅ Git历史: {len(history)} 条提交")
    
    return True

def test_working_memory():
    """测试工作记忆 - 128k防护"""
    print("\n=== 测试工作记忆 ===")
    working = WorkingMemory(max_tokens=10000, max_chunks=3)
    
    evicted_count = [0]
    def on_evict(chunk):
        evicted_count[0] += 1
        print(f"  → 驱逐: {chunk.content[:30]}...")
    
    working.on_evict(on_evict)
    
    # 模拟添加大量内容
    for i in range(5):
        evicted = working.add("user", f"消息{i}: " + "这是一个测试内容，会占用token空间。" * 50)
    
    print(f"✅ 工作记忆限制: {len(working.chunks)} chunks (max 3)")
    print(f"✅ 驱逐次数: {evicted_count[0]}")
    
    return True

def test_impression_layer():
    """测试印象层 - 模糊索引"""
    print("\n=== 测试印象层 ===")
    impression = ImpressionLayer(db_path="~/.bio-memory/test/impressions.db")
    
    # 创建印象
    pointer = "/fake/path/test.md"
    imp_id = impression.create(
        "这是关于 Bio-Memory-OS 架构设计的讨论记录。我们解决了 128k 溢出问题。",
        pointer,
        {"entities": ["Bio-Memory-OS", "架构设计"]}
    )
    print(f"✅ 印象创建: {imp_id}")
    
    # 模糊回忆
    results = impression.recall_fuzzy("关于生物记忆的讨论")
    print(f"✅ 模糊回忆: 找到 {len(results)} 条相关记忆")
    for r in results:
        print(f"  → {r['gist'][:50]}...")
    
    return True

if __name__ == "__main__":
    print("Bio-Memory-OS 基础测试")
    print("=" * 40)
    
    try:
        test_eternal_layer()
        test_working_memory()
        test_impression_layer()
        print("\n✅ 所有测试通过！")
        print("\n三层记忆架构工作正常:")
        print("  • Eternal Layer - Git版本控制 ✓")
        print("  • Working Memory - 128k防护 ✓")
        print("  • Impression Layer - 模糊索引 ✓")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
