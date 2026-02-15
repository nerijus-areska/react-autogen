from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import os
import re
from pathlib import Path
from app.core.models import Session

class LLMParseError(Exception):
    """Raised when an LLM response could not be parsed correctly (e.g. invalid JSON)."""
    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response


class BaseWorkflow(ABC):
    """
    Abstract base class for all AI code modification workflows.
    
    Each workflow represents a different strategy for applying changes to a codebase.
    Workflows modify files directly in the session_path and don't return results -
    git handles tracking what changed.
    """
    
    # Metadata - must be set by subclasses
    name: str = None  # e.g., "simple_modification"
    description: str = None  # e.g., "Basic file identification and single-pass modification"
    complexity_level: str = None  # "simple" | "medium" | "complex"
    estimated_tokens: int = 0  # Rough estimate for router decision-making
    
    def __init__(self):
        """Initialize workflow and validate metadata."""
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define 'name'")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} must define 'description'")
        if not self.complexity_level:
            raise ValueError(f"{self.__class__.__name__} must define 'complexity_level'")
    
    @abstractmethod
    async def apply_changes(self, session: Session, instruction: str) -> None:
        """
        Apply the requested changes to the codebase.
        
        This method should modify files directly in session_path.
        It does NOT return anything - git diff will show what changed.
        
        Args:
            session: Session dictionary containing session_id and session_path
            instruction: Natural language instruction from the user
            
        Raises:
            Exception: If the workflow fails to apply changes
        """
        pass
    
    
    # Helpers

    def _normalize_path(self, path: str) -> str:
        """
        Normalize paths so 'src/...' or 'src\\...' works when the workflow root is already .../src.
        Use for directory and file paths coming from the LLM (e.g. from a file tree rooted at src).
        """
        if not path or path == ".":
            return path or "."
        normalized = path.replace("\\", "/").strip("/")
        if normalized == "src":
            return "."
        if normalized.startswith("src/"):
            return normalized[4:] or "."
        return path

    def _normalize_file_pattern(self, file_pattern: str) -> str:
        """
        Normalize file_pattern for grep --include: strip src/ prefix and use basename glob,
        since grep --include matches against the file basename only.
        """
        if not file_pattern or file_pattern == "*":
            return file_pattern or "*"
        p = file_pattern.replace("\\", "/").strip("/")
        if p.startswith("src/"):
            p = p[4:] or "*"
        if "/" in p:
            p = p.split("/")[-1]
        return p or "*"

    def _extract_json_from_response(self, response: str, threshold_percentage: float = 0.2) -> str:
        """
        Extract the string to use for JSON parsing from an LLM response.

        If the response contains a JSON block (markdown code block or raw {...})
        and that block is at least x% of the response length, returns that block.
        Otherwise returns the full response (with markdown code fences stripped).

        This helps when the LLM wraps JSON in prose or multiple blocks.
        """
        text = response.strip()
        if not text:
            return text
        original_len = len(text)
        threshold = original_len * threshold_percentage
        candidates = []

        # 1. Markdown code blocks: ```json ... ``` or ``` ... ```
        for pattern in (r"```(?:json)?\s*\n(.*?)\n```", r"```(?:json)?\s*\n(.*?)```"):
            for match in re.finditer(pattern, text, re.DOTALL):
                block = match.group(1).strip()
                if len(block) >= threshold:
                    candidates.append(block)
        # 2. Raw JSON object: find outermost balanced { ... }
        start = text.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        block = text[start : i + 1]
                        if len(block) >= threshold:
                            candidates.append(block)
                        break

        if candidates:
            # Prefer the longest candidate (most likely the main payload)
            best = max(candidates, key=len)
            return best

        # No qualifying block: strip markdown code fences and return full text
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].strip() in ("```json", "```"):
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
        return text.strip()

    def _build_file_tree(self, session_path: str, max_depth: int = 5) -> dict:
        """
        Build a file tree representation of the codebase.
        
        Args:
            session_path: Path to the repository
            max_depth: Maximum directory depth to traverse
            
        Returns:
            Dictionary representing the file tree structure
        """
        from app.core.file_ops import generate_file_tree
        return generate_file_tree(session_path, max_depth)

    # --- File outline (imports, components, functions) - shared by tree display and get_file_structure tool ---

    _OUTLINE_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx")

    def _get_file_outline(self, session_path: str, relative_path: str) -> Dict[str, list]:
        """
        Parse a JS/TS file and return a structured outline: imports, components, functions.
        Used both for enhanced file trees (simple workflow) and get_file_structure tool (explorative).
        
        Args:
            session_path: Root path of the repository
            relative_path: Path to the file relative to session_path
            
        Returns:
            {"imports": [...], "components": [...], "functions": [...]}
        """
        try:
            content = self._load_file(session_path, relative_path)
        except Exception:
            return {"imports": [], "components": [], "functions": []}
        imports = re.findall(r"^import\s+.*$", content, re.MULTILINE)
        components = []
        components.extend(re.findall(r"function\s+([A-Z][A-Za-z0-9]*)", content))
        components.extend(re.findall(r"const\s+([A-Z][A-Za-z0-9]*)\s*=.*?=>", content, re.DOTALL))
        functions = []
        for m in re.finditer(
            r"^(?:export\s+)?(?:const|function)\s+([A-Za-z_][A-Za-z0-9_]*)",
            content,
            re.MULTILINE,
        ):
            functions.append(m.group(1))
        return {
            "imports": imports,
            "components": list(dict.fromkeys(components)),
            "functions": list(dict.fromkeys(functions)),
        }

    def _format_file_outline_for_tree(self, outline: Dict[str, list], max_names: int = 5) -> str:
        """
        Format outline for a single line in a file tree (e.g. " - Functions: A, B, C").
        """
        names = (outline.get("components") or []) + (outline.get("functions") or [])
        names = list(dict.fromkeys(names))[:max_names]
        if not names:
            return ""
        return f" - Functions: {', '.join(names)}"

    def _format_file_structure_response(self, file_path: str, outline: Dict[str, list]) -> str:
        """
        Format outline as full get_file_structure tool response (imports, components, functions sections).
        """
        parts = [f"File: {file_path}\n"]
        imports = outline.get("imports") or []
        if imports:
            parts.append("Imports:")
            for imp in imports[:10]:
                parts.append(f"  {imp}")
            if len(imports) > 10:
                parts.append(f"  ... and {len(imports) - 10} more imports")
            parts.append("")
        components = outline.get("components") or []
        if components:
            parts.append("Components:")
            for c in components:
                parts.append(f"  - {c}")
            parts.append("")
        functions = outline.get("functions") or []
        if functions:
            parts.append("Functions/Constants:")
            for f in functions:
                parts.append(f"  - {f}")
        return "\n".join(parts)
    
    def _load_file(self, session_path: str, relative_path: str) -> str:
        """
        Load content of a single file.
        
        Args:
            session_path: Root path of the repository
            relative_path: Path relative to session_path
            
        Returns:
            File content as string
        """
        full_path = os.path.join(session_path, relative_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _write_file(self, session_path: str, relative_path: str, content: str) -> None:
        """
        Write content to a file, creating directories if needed.
        
        Args:
            session_path: Root path of the repository
            relative_path: Path relative to session_path
            content: Content to write
        """
        full_path = os.path.join(session_path, relative_path)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _delete_file(self, session_path: str, relative_path: str) -> None:
        """
        Delete a file from the repository.
        
        Args:
            session_path: Root path of the repository
            relative_path: Path relative to session_path
        """
        full_path = os.path.join(session_path, relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    
    def _list_files(self, session_path: str, pattern: str = "**/*") -> list[str]:
        """
        List all files matching a pattern.
        
        Args:
            session_path: Root path of the repository
            pattern: Glob pattern (default: all files)
            
        Returns:
            List of relative file paths
        """
        base_path = Path(session_path)
        return [
            str(p.relative_to(base_path))
            for p in base_path.glob(pattern)
            if p.is_file()
        ]
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' complexity='{self.complexity_level}'>"