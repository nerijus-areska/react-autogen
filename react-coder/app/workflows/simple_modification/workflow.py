from app.workflows.base import BaseWorkflow, LLMParseError
from app.workflows.registry import WorkflowRegistry
from app.core.llm import get_llm_client
from app.core.file_ops import generate_file_tree, load_files, get_file_stats
import json
from typing import Dict, List, Any
import logging
from pathlib import Path
from app.core.models import Session
from app.core.llm import LLMClient

logger = logging.getLogger(__name__)

@WorkflowRegistry.register
class SimpleModificationWorkflow(BaseWorkflow):
    """
    Basic file identification and single-pass modification workflow.
    
    Steps:
    1. Build enhanced file tree with metadata (sizes, function names)
    2. LLM identifies which files need modification
    3. Load identified files
    4. LLM generates complete modified file contents
    5. Write modifications to filesystem
    """
    
    name = "simple_modification"
    description = "Basic file identification and single-pass modification. Best for simple styling, text changes, or single-component edits."
    complexity_level = "simple"
    
    async def apply_changes(self, session: Session, instruction: str) -> None:
        """
        Apply changes using a two-step LLM process.
        
        Args:
            session: Session dictionary containing session_id and session_path
            instruction: Natural language instruction from user
        """
        llm = get_llm_client()
        session_path = Path(session.path).joinpath("src")
        
        file_tree_info = self._build_enhanced_file_tree(session_path)
        
        relevant_files = await self._identify_files(session, llm, instruction, file_tree_info)
        
        if not relevant_files:
            logger.info("No files identified for modification")
            return

        relevant_files = [self._normalize_path(f) for f in relevant_files]
        logger.info(f"Identified files: {relevant_files}")
        
        file_contents = load_files(session_path, relevant_files)
        
        if not file_contents:
            logger.info("No file contents loaded")
            return
        
        modifications = await self._generate_modifications(session, llm, instruction, file_contents)
        
        if not modifications:
            logger.info("No modifications generated")
            return
        
        for filepath, content in modifications.items():
            normalized_path = self._normalize_path(filepath)
            logger.info(f"Writing modifications to {normalized_path}")
            self._write_file(session_path, normalized_path, content)
    
    def _build_enhanced_file_tree(self, session_path: str) -> str:
        """
        Build a detailed file tree representation with metadata.
        
        Includes:
        - File paths and sizes
        - Function/component names extracted from JS/JSX files
        - Project statistics
        
        Args:
            session_path: Root path of the repository
            
        Returns:
            Formatted string with file tree and metadata
        """
        tree = generate_file_tree(session_path, max_depth=5, include_metadata=True)
        stats = get_file_stats(session_path)
        
        tree_text = self._tree_to_text_with_functions(session_path, tree)
        
        summary = f"""Project Structure:
            Total files: {stats['total_files']}
            Files by type: {stats['files_by_type']}

            File Tree:
            {tree_text}
            """
        return summary
    
    def _tree_to_text_with_functions(self, session_path: str, node: dict, indent: int = 0) -> str:
        """
        Convert tree dict to indented text with function names.
        
        Args:
            session_path: Root path to read files from
            node: Tree node dict
            indent: Current indentation level
            
        Returns:
            Formatted tree text
        """
        lines = []
        prefix = "  " * indent
        
        if node["type"] == "file":
            size_kb = node.get("size", 0) / 1024
            line = f"{prefix}├── {node['name']} ({size_kb:.1f}KB)"
            
            if node.get("extension") in self._OUTLINE_EXTENSIONS:
                outline = self._get_file_outline(session_path, node["path"])
                suffix = self._format_file_outline_for_tree(outline)
                if suffix:
                    line += suffix
            
            lines.append(line)
        else:
            lines.append(f"{prefix}├── {node['name']}/")
            for child in node.get("children", []):
                lines.append(self._tree_to_text_with_functions(session_path, child, indent + 1))
        
        return "\n".join(lines)

    def _previous_commands_block(self, session: Session) -> str:
        """Format previous user commands for context in prompts (current task is passed separately)."""
        previous = session.user_questions[:-1] if len(session.user_questions) > 1 else []
        if not previous:
            return ""
        return "\nPREVIOUS USER COMMANDS (for context; current task is below):\n" + "\n".join(f"- {q}" for q in previous) + "\n\n"

    async def _identify_files(self, session: Session, llm: LLMClient, instruction: str, file_tree: str) -> List[str]:
        """
        Use LLM to identify which files need modification.
        
        Args:
            llm: LLM client instance
            instruction: User's instruction
            file_tree: Enhanced file tree string
            
        Returns:
            List of relative file paths to modify
        """
        previous_block = self._previous_commands_block(session)
        prompt = f"""You are analyzing a Vite/React/Tailwind CSS codebase to determine which files need to be modified.
{previous_block}
{file_tree}

User instruction: "{instruction}"

Analyze the instruction and file structure. Identify which files need to be modified to fulfill this instruction.

Guidelines:
- Be selective - only include files that will actually change
- Consider component hierarchy and imports
- For styling changes, include relevant CSS files
- For component changes, include the component file and possibly parent files

Return ONLY a JSON array of file paths, like: ["src/App.jsx", "src/styles.css"]
No explanation, just the JSON array.
"""
        
        response = await llm.invoke(prompt, session=session)
        
        try:
            files = self._parse_json_response(response)
            
            if not isinstance(files, list):
                raise LLMParseError(
                    "LLM response for file list is not a JSON array",
                    raw_response=response[:500],
                )
            
            return [f for f in files if isinstance(f, str)]
        
        except LLMParseError:
            raise
        except Exception as e:
            raise LLMParseError(
                f"Failed to parse file list from LLM: {e}",
                raw_response=response[:500],
            ) from e
    
    async def _generate_modifications(
        self, 
        session: Session,
        llm, 
        instruction: str,   
        file_contents: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Use LLM to generate modifications for identified files.
        
        Args:
            llm: LLM client instance
            instruction: User's instruction
            file_contents: Dict mapping file paths to their current contents
            
        Returns:
            Dict mapping file paths to their new contents
        """
        # Build prompt with all file contents
        files_section = []
        for filepath, content in file_contents.items():
            files_section.append(f"""
FILE: {filepath}
{'=' * 80}
{content}
{'=' * 80}
""")
        
        files_text = "\n".join(files_section)
        previous_block = self._previous_commands_block(session)
        prompt = f"""You are modifying a React codebase based on user instructions.
{previous_block}
User instruction: "{instruction}"

Current files:
{files_text}

Modify the files according to the instruction. 

IMPORTANT:
- Return the COMPLETE modified content for EACH file
- Do NOT return partial files or just the changes
- Maintain proper syntax (React/JavaScript/CSS)
- Keep all existing code that isn't affected by the instruction
- Ensure imports and exports are correct

Return your response as a JSON object where keys are file paths and values are the complete new file contents:

{{
  "src/App.jsx": "complete file content here...",
  "src/styles.css": "complete file content here..."
}}

Return ONLY the JSON object. No explanation or markdown formatting.
"""
        
        response = await llm.invoke(prompt, session=session)
        
        # Parse JSON response
        try:
            modifications = self._parse_json_response(response)
            
            if not isinstance(modifications, dict):
                raise LLMParseError(
                    "LLM response for modifications is not a JSON object",
                    raw_response=response[:500],
                )
            
            return modifications
        
        except LLMParseError:
            raise
        except Exception as e:
            raise LLMParseError(
                f"Failed to parse modifications from LLM: {e}",
                raw_response=response[:500],
            ) from e
    
    def _parse_json_response(self, response: str):
        """
        Parse JSON from LLM response, handling markdown code blocks.

        Raises:
            LLMParseError: If the response cannot be parsed as valid JSON.
        """
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first line (```json) and last line (```)
            response = "\n".join(lines[1:-1])

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise LLMParseError(
                f"Invalid JSON in LLM response: {e}",
                raw_response=response[:500],
            ) from e
