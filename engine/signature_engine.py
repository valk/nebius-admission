import tree_sitter_languages
from tree_sitter import Node
from typing import List, Dict, Any, Optional

class SignatureEngine:
    def __init__(self):
        self.parsers = {}
        # Map common extensions to tree-sitter language names
        self.extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "cpp",
            ".java": "java",
            "package.json": "json",
            "requirements.txt": None, # Direct parsing for manifests
        }

    def _get_parser(self, lang_name: str):
        if lang_name not in self.parsers:
            try:
                self.parsers[lang_name] = tree_sitter_languages.get_parser(lang_name)
            except Exception:
                return None
        return self.parsers[lang_name]

    def extract_signatures(self, file_path: str, code: str) -> str:
        ext = "." + file_path.split(".")[-1] if "." in file_path else file_path
        lang_name = self.extension_map.get(ext)
        if not lang_name:
            return "" # Skip if not supported or not a code file

        parser = self._get_parser(lang_name)
        if not parser:
            return ""

        tree = parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        signatures = []
        self._traverse_node(root_node, code, signatures, lang_name)
        
        return "\n".join(signatures)

    def _traverse_node(self, node: Node, code: str, signatures: List[str], lang_name: str, depth: int = 0):
        # This is a simplified traversal. For better results, use language-specific queries.
        # But for "Universal", we look for common node types.
        
        node_type = node.type
        is_signature = False
        
        # Heuristics for signatures across languages
        if node_type in ["function_definition", "class_definition", "method_definition", "function_declaration", "method_declaration", "function_item"]:
            is_signature = True
        
        if is_signature:
            # Extract only the signature part, not the body
            # Typically, we want everything up to the first '{' or ':' (for Python)
            # Or use tree-sitter child nodes to find the identifier and parameters
            
            sig_text = self._get_signature_text(node, code, lang_name)
            docstring = self._get_docstring(node, code, lang_name)
            
            indent = "  " * depth
            if docstring:
                signatures.append(f"{indent}{docstring}")
            signatures.append(f"{indent}{sig_text}")
            
            # Recurse into classes to find methods, but don't recurse into function bodies
            if node_type == "class_definition":
                for child in node.children:
                    self._traverse_node(child, code, signatures, lang_name, depth + 1)
        else:
            # Continue searching for definitions in the rest of the file
            for child in node.children:
                # Avoid going into blocks or bodies if we are not in a class
                if child.type not in ["block", "compound_statement", "function_body"]:
                    self._traverse_node(child, code, signatures, lang_name, depth)

    def _get_signature_text(self, node: Node, code: str, lang_name: str) -> str:
        # Try to find the declaration/header part
        # A simple way is to find the first child that is a block or colon and take everything before it
        # Or just use the first few lines of the node
        
        lines = node.text.decode("utf8").splitlines()
        if not lines:
            return ""
            
        # Specific logic for Python (colon)
        if lang_name == "python":
            for i, line in enumerate(lines):
                if ":" in line:
                    return "\n".join(lines[:i+1])
            return lines[0]
            
        # Specific logic for C-style (opening brace)
        for i, line in enumerate(lines):
            if "{" in line:
                return "\n".join(lines[:i+1]).split("{")[0].strip() + " { ... }"
        
        return lines[0]

    def _get_docstring(self, node: Node, code: str, lang_name: str) -> Optional[str]:
        # Simple docstring extraction: check previous sibling or first child (for Python)
        if lang_name == "python":
            # Check for a string literal as the first child of the body
            # For simplicity, let's just look at the lines before the node
            pass
            
        # Look for comments immediately preceding the node
        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type in ["comment", "line_comment", "block_comment"]:
            return prev_sibling.text.decode("utf8")
        return None
