import os
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

class EternalLayer:
    """不可变存储层 - 基于 Git 的版本控制"""
    
    def __init__(self, base_path: str = "~/.bio-memory/eternal"):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._init_git()
    
    def _init_git(self):
        """自动初始化 Git 仓库"""
        git_dir = self.base_path / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=self.base_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "bio@memory.local"], 
                          cwd=self.base_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "BioMemory"], 
                          cwd=self.base_path, capture_output=True)
    
    def store(self, content: str, metadata: Dict) -> str:
        """
        存储内容，自动提交 Git
        返回：文件路径（作为指针）
        """
        # 按时间组织目录：2026/03/25/
        now = datetime.now()
        relative_path = f"{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}-{now.minute:02d}-{metadata.get('type', 'memory')}.md"
        file_path = self.base_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 计算内容哈希
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # 构建文件头
        header = f"""---
timestamp: {now.isoformat()}
type: {metadata.get('type', 'text')}
title: {metadata.get('title', 'untitled')}
hash: {content_hash}
tags: {metadata.get('tags', [])}
---

"""
        full_content = header + content
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # Git 提交
        try:
            subprocess.run(["git", "add", str(file_path)], cwd=self.base_path, check=True, capture_output=True)
            commit_msg = metadata.get('title', 'update')[:50] # 限制长度
            subprocess.run(["git", "commit", "-m", f"{commit_msg}"], 
                          cwd=self.base_path, capture_output=True)
        except subprocess.CalledProcessError:
            pass # 如果没有变化，忽略错误
        
        return str(file_path)
    
    def retrieve(self, pointer: str, verify_hash: bool = False) -> str:
        """
        根据指针检索内容
        pointer: 文件路径（绝对路径或相对于 base_path）
        """
        if not pointer.startswith(str(self.base_path)):
            pointer = str(self.base_path / pointer)
        
        with open(pointer, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if verify_hash:
            # 提取存储的哈希
            lines = content.split('\n')
            stored_hash = None
            for line in lines:
                if line.startswith('hash:'):
                    stored_hash = line.split(':')[1].strip()
                    break
            
            # 验证
            body = '\n'.join(lines[lines.index('---')+2 if '---' in lines else 0:])
            actual_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
            if stored_hash and stored_hash != actual_hash:
                raise ValueError(f"Hash mismatch! Memory tampered: {pointer}")
        
        return content
    
    def get_history(self, pointer: str) -> list:
        """获取文件的 Git 历史"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", pointer], 
                cwd=self.base_path, 
                capture_output=True, 
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n')
        except:
            return []
