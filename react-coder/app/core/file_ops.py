from pathlib import Path
from typing import List, Dict, Optional


IGNORE_PATTERNS = {
    'node_modules',
    '.git',
    '.next',
    'dist',
    'build',
    '__pycache__',
    '.pytest_cache',
    'coverage',
    '.vscode',
    '.idea',
    'venv',
    'env',
    '.env',
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',
}

# for React project
RELEVANT_EXTENSIONS = {
    '.js',
    '.jsx',
    '.ts',
    '.tsx',
    '.css',
    '.scss',
    '.json',
    '.html',
}


def generate_file_tree(
    session_path: str,
    max_depth: int = 5,
    include_metadata: bool = True
) -> dict:
    """
    Generate a hierarchical file tree representation of the codebase.
    
    Args:
        session_path: Root path to scan
        max_depth: Maximum directory depth to traverse
        include_metadata: Include file sizes and types
        
    Returns:
        Dictionary with file tree structure:
        {
            "name": "project-name",
            "type": "directory",
            "children": [
                {"name": "src", "type": "directory", "children": [...]},
                {"name": "App.jsx", "type": "file", "size": 1234, "extension": ".jsx"}
            ]
        }
    """
    base_path = Path(session_path)
    
    def build_tree(path: Path, current_depth: int = 0) -> Optional[dict]:
        if current_depth > max_depth:
            return None
        
        if path.name in IGNORE_PATTERNS:
            return None
        
        if path.is_file():
            if path.suffix not in RELEVANT_EXTENSIONS:
                return None
            
            node = {
                "name": path.name,
                "type": "file",
                "path": str(path.relative_to(base_path))
            }
            
            if include_metadata:
                node["size"] = path.stat().st_size
                node["extension"] = path.suffix
            
            return node
        
        elif path.is_dir():
            children = []
            try:
                for child in sorted(path.iterdir()):
                    child_node = build_tree(child, current_depth + 1)
                    if child_node:
                        children.append(child_node)
            except PermissionError:
                return None
            
            if not children:
                return None
            
            return {
                "name": path.name,
                "type": "directory",
                "path": str(path.relative_to(base_path)) if path != base_path else ".",
                "children": children
            }
        
        return None
    
    tree = build_tree(base_path)
    return tree if tree else {"name": base_path.name, "type": "directory", "children": []}


def generate_file_list(session_path: str) -> List[str]:
    """
    Generate a flat list of all relevant files in the codebase.
    
    Args:
        session_path: Root path to scan
        
    Returns:
        List of relative file paths
    """
    base_path = Path(session_path)
    files = []
    
    for path in base_path.rglob('*'):
        if any(ignored in path.parts for ignored in IGNORE_PATTERNS):
            continue
        
        if path.is_file() and path.suffix in RELEVANT_EXTENSIONS:
            files.append(str(path.relative_to(base_path)))
    
    return sorted(files)


def load_files(session_path: str, file_paths: List[str]) -> Dict[str, str]:
    """
    Load content of multiple files.
    
    Args:
        session_path: Root path of the repository
        file_paths: List of relative file paths to load
        
    Returns:
        Dictionary mapping file paths to their content
    """
    result = {}
    base_path = Path(session_path)
    
    for file_path in file_paths:
        full_path = base_path / file_path
        
        if not full_path.exists():
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                result[file_path] = f.read()
        except (UnicodeDecodeError, PermissionError):
            continue
    
    return result


def get_project_structure_summary(session_path: str) -> str:
    """
    Generate a human-readable summary of the project structure.
    Useful for LLM prompts.
    
    Args:
        session_path: Root path of the repository
        
    Returns:
        Text summary of project structure
    """
    tree = generate_file_tree(session_path, max_depth=3, include_metadata=False)
    
    def tree_to_text(node: dict, indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent
        
        if node["type"] == "file":
            lines.append(f"{prefix}├── {node['name']}")
        else:
            lines.append(f"{prefix}├── {node['name']}/")
            for child in node.get("children", []):
                lines.extend(tree_to_text(child, indent + 1))
        
        return lines
    
    lines = [tree["name"] + "/"]
    for child in tree.get("children", []):
        lines.extend(tree_to_text(child, 0))
    
    return "\n".join(lines)


def count_tokens_estimate(content: str) -> int:

    return len(content) // 4


def get_file_stats(session_path: str) -> dict:
    """
    Get statistics about the codebase.
    
    Args:
        session_path: Root path of the repository
        
    Returns:
        Dictionary with stats:
        {
            "total_files": int,
            "total_lines": int,
            "files_by_type": {"jsx": 5, "css": 2, ...},
            "estimated_tokens": int
        }
    """
    base_path = Path(session_path)
    stats = {
        "total_files": 0,
        "total_lines": 0,
        "files_by_type": {},
        "estimated_tokens": 0
    }
    
    for path in base_path.rglob('*'):
        if any(ignored in path.parts for ignored in IGNORE_PATTERNS):
            continue
        
        if path.is_file() and path.suffix in RELEVANT_EXTENSIONS:
            stats["total_files"] += 1
            
            ext = path.suffix.lstrip('.')
            stats["files_by_type"][ext] = stats["files_by_type"].get(ext, 0) + 1
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    stats["total_lines"] += content.count('\n')
                    stats["estimated_tokens"] += count_tokens_estimate(content)
            except (UnicodeDecodeError, PermissionError):
                continue
    
    return stats