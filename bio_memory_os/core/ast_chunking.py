from tree_sitter import Language, Parser
from typing import List, Dict, Optional
from pathlib import Path
import tree_sitter_python

class ASTChunking:
    """AST感知分块器 - 优化代码类记忆的检索效果"""
    
    def __init__(self):
        # 初始化Python解析器
        self.PY_LANGUAGE = Language(tree_sitter_python.language())
        self.parser = Parser(self.PY_LANGUAGE)
        self.supported_languages = {
            "py": self.PY_LANGUAGE,
            "python": self.PY_LANGUAGE
        }
        print("[BMO AST] 📝 代码AST分块器初始化完成，支持Python")
    
    def is_code_file(self, file_path: str) -> bool:
        """判断是否为支持的代码文件"""
        ext = Path(file_path).suffix.lower()[1:]
        return ext in self.supported_languages
    
    def chunk_code(self, content: str, language: str = "python") -> List[Dict]:
        """
        基于AST智能分块代码，按函数/类/模块分割
        返回分块列表：每个块包含类型、名称、起始行、内容
        """
        if language not in self.supported_languages:
            return self._fallback_chunk(content)
        
        parser = Parser(self.supported_languages[language])
        tree = parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        
        chunks = []
        lines = content.split('\n')
        
        def extract_node_content(node):
            """提取节点对应的文本内容"""
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            return '\n'.join(lines[start_line:end_line+1])
        
        # 遍历顶级节点
        for child in root_node.children:
            if child.type == "function_definition":
                # 提取函数定义
                name_node = child.child_by_field_name("name")
                if name_node:
                    func_name = name_node.text.decode("utf8")
                    chunks.append({
                        "type": "function",
                        "name": func_name,
                        "start_line": child.start_point[0] + 1,
                        "end_line": child.end_point[0] + 1,
                        "content": extract_node_content(child),
                        "entities": [func_name]
                    })
            
            elif child.type == "class_definition":
                # 提取类定义
                name_node = child.child_by_field_name("name")
                if name_node:
                    class_name = name_node.text.decode("utf8")
                    class_content = extract_node_content(child)
                    chunks.append({
                        "type": "class",
                        "name": class_name,
                        "start_line": child.start_point[0] + 1,
                        "end_line": child.end_point[0] + 1,
                        "content": class_content,
                        "entities": [class_name]
                    })
                    
                    # 提取类内的方法
                    for class_child in child.children:
                        if class_child.type == "block":
                            for block_child in class_child.children:
                                if block_child.type == "function_definition":
                                    method_name_node = block_child.child_by_field_name("name")
                                    if method_name_node:
                                        method_name = method_name_node.text.decode("utf8")
                                        chunks.append({
                                            "type": "method",
                                            "name": f"{class_name}.{method_name}",
                                            "start_line": block_child.start_point[0] + 1,
                                            "end_line": block_child.end_point[0] + 1,
                                            "content": extract_node_content(block_child),
                                            "entities": [class_name, method_name]
                                        })
        
        # 如果没有识别到结构，使用回退分块
        if not chunks:
            return self._fallback_chunk(content)
        
        return chunks
    
    def _fallback_chunk(self, content: str, chunk_size: int = 100) -> List[Dict]:
        """回退分块策略：按固定大小分块"""
        lines = content.split('\n')
        chunks = []
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i+chunk_size]
            chunks.append({
                "type": "code_fallback",
                "name": f"chunk_{i//chunk_size + 1}",
                "start_line": i + 1,
                "end_line": min(i + chunk_size, len(lines)),
                "content": '\n'.join(chunk_lines),
                "entities": []
            })
        return chunks
    
    def extract_code_entities(self, content: str, language: str = "python") -> List[str]:
        """提取代码中的实体（函数名、类名、变量名等）"""
        if language not in self.supported_languages:
            return []
        
        parser = Parser(self.supported_languages[language])
        tree = parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        
        entities = set()
        
        def traverse(node):
            if node.type == "identifier":
                name = node.text.decode("utf8")
                if len(name) > 2:  # 过滤短变量名
                    entities.add(name)
            
            for child in node.children:
                traverse(child)
        
        traverse(root_node)
        return list(entities)
    
    def enhance_impression(self, content: str, file_path: str = None) -> Dict:
        """增强代码记忆的印象层索引"""
        if file_path and self.is_code_file(file_path):
            ext = Path(file_path).suffix.lower()[1:]
            chunks = self.chunk_code(content, ext)
            entities = set()
            for chunk in chunks:
                entities.update(chunk["entities"])
            
            return {
                "is_code": True,
                "language": ext,
                "entities": list(entities),
                "chunk_count": len(chunks),
                "chunks": chunks
            }
        
        return {"is_code": False}
