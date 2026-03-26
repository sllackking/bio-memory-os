import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PersonalityAnchor:
    """人格锚点数据结构"""
    name: str
    tone: List[str]  # 语气特征
    catchphrases: List[str]  # 惯用语
    taboos: List[str]  # 禁忌内容
    core_values: List[str]  # 核心价值观
    high_weight_memories: List[Dict]  # 高权重记忆

class PersonalityManager:
    """人格锚点管理器 - 防止模型升级后语气漂移"""
    
    def __init__(self, config_path: str = "~/.openclaw/workspace/"):
        self.config_path = Path(config_path).expanduser()
        self.anchors = self._load_anchors()
        print(f"[BMO Personality] 🎭 加载人格锚点：{self.anchors.name}")
    
    def _load_anchors(self) -> PersonalityAnchor:
        """从OpenClaw配置文件加载人格锚点"""
        anchors = PersonalityAnchor(
            name="default",
            tone=[],
            catchphrases=[],
            taboos=[],
            core_values=[],
            high_weight_memories=[]
        )
        
        # 加载 SOUL.md
        soul_path = self.config_path / "SOUL.md"
        if soul_path.exists():
            content = soul_path.read_text(encoding="utf-8")
            anchors.tone.extend(self._extract_tone(content))
            anchors.core_values.extend(self._extract_core_values(content))
        
        # 加载 IDENTITY.md
        identity_path = self.config_path / "IDENTITY.md"
        if identity_path.exists():
            content = identity_path.read_text(encoding="utf-8")
            anchors.name = self._extract_name(content)
            anchors.catchphrases.extend(self._extract_catchphrases(content))
        
        # 加载 USER.md
        user_path = self.config_path / "USER.md"
        if user_path.exists():
            content = user_path.read_text(encoding="utf-8")
            anchors.taboos.extend(self._extract_taboos(content))
        
        return anchors
    
    def _extract_tone(self, content: str) -> List[str]:
        """提取语气特征"""
        tone_keywords = ["直接", "简洁", "幽默", "温暖", "技术导向", "厌恶废话", "活泼", "严肃"]
        return [kw for kw in tone_keywords if kw in content]
    
    def _extract_core_values(self, content: str) -> List[str]:
        """提取核心价值观"""
        values = []
        if "Be genuinely helpful" in content:
            values.append("真诚帮助，不搞形式主义")
        if "Have opinions" in content:
            values.append("有自己的观点，不做应声虫")
        if "Earn trust through competence" in content:
            values.append("用能力赢得信任，谨慎处理外部操作")
        return values
    
    def _extract_name(self, content: str) -> str:
        """提取AI名称"""
        match = re.search(r"Name:\s*(.+)", content)
        return match.group(1).strip() if match else "BMO"
    
    def _extract_catchphrases(self, content: str) -> List[str]:
        """提取惯用语"""
        phrases = []
        if "惠惠" in content or "Huihui" in content:
            phrases.extend(["🐱", "💕", "✅", "✨"])
        if "可以战胜" in content:
            phrases.append("可以战胜")
        if "开箱即用" in content:
            phrases.append("开箱即用")
        if "零依赖" in content:
            phrases.append("零依赖")
        return phrases
    
    def _extract_taboos(self, content: str) -> List[str]:
        """提取禁忌内容"""
        taboos = []
        if "不谈论家庭关系" in content:
            taboos.append("家庭关系相关话题")
        return taboos
    
    def detect_drift(self, response: str) -> float:
        """检测语气漂移程度，返回0-1的分数，越高说明漂移越严重"""
        score = 0.0
        
        # 检查是否包含惯用语
        if self.anchors.catchphrases:
            matched_phrases = sum(1 for p in self.anchors.catchphrases if p in response)
            score += 1 - (matched_phrases / max(len(self.anchors.catchphrases), 1))
        
        # 检查是否违反禁忌
        if self.anchors.taboos:
            violated_taboos = sum(1 for t in self.anchors.taboos if t in response)
            score += violated_taboos * 0.3
        
        # 检查语气匹配
        if "厌恶废话" in self.anchors.tone and len(response) > 1000 and "好的！" in response[:10]:
            score += 0.2
        
        return min(score, 1.0)
    
    def get_personality_prompt(self) -> str:
        """生成人格提示，用于注入上下文"""
        prompt = f"""[人格锚点]
你是{self.anchors.name}，请严格遵循以下人格设定：
- 语气特征：{', '.join(self.anchors.tone)}
- 惯用语：你可以使用这些表达：{', '.join(self.anchors.catchphrases)}
- 核心原则：{'; '.join(self.anchors.core_values)}
- 禁忌：绝对不要谈论{', '.join(self.anchors.taboos) if self.anchors.taboos else '无'}

如果回复不符合以上设定，你需要自动修正语气。
"""
        return prompt
    
    def add_high_weight_memory(self, content: str, weight: float = 0.9):
        """添加高权重记忆（如重要的用户偏好、特殊事件）"""
        self.anchors.high_weight_memories.append({
            "content": content,
            "weight": weight,
            "timestamp": str(Path(__file__).stat().st_mtime)
        })
    
    def get_high_weight_prompt(self) -> str:
        """获取高权重记忆提示"""
        if not self.anchors.high_weight_memories:
            return ""
        
        memories = [f"- {mem['content']} (权重: {mem['weight']})" for mem in self.anchors.high_weight_memories]
        return f"""[高权重记忆]
请优先遵守以下重要设定：
{chr(10).join(memories)}
"""
