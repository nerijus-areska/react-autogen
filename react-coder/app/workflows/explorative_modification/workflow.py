from app.workflows.base import BaseWorkflow, LLMParseError
from app.workflows.registry import WorkflowRegistry
from app.core.llm import get_llm_client, write_workflow_log
from app.core.file_ops import generate_file_tree
import json
import subprocess
import time
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
from app.core.models import Session
from app.core.llm import LLMClient
import os

logger = logging.getLogger(__name__)

@WorkflowRegistry.register
class ExplorativeModificationWorkflow(BaseWorkflow):
    """
    Tool-based agentic exploration workflow.
    
    Instead of loading entire files, gives the LLM tools to explore the codebase:
    - grep_code: Search for patterns in files
    - search_symbol: Find function/variable definitions and usages
    - read_file_lines: Read specific line ranges
    - list_files: List directory contents
    - get_file_structure: Get file outline (imports, function signatures)
    - apply_edit: Make targeted str_replace edits
    
    The LLM iteratively uses these tools to understand the codebase and make changes.
    """
    
    name = "explorative_modification"
    description = "Advanced workflow using tool-based exploration. LLM explores codebase with grep/search tools and makes targeted edits. Best for complex multi-file changes."
    complexity_level = "advanced"
    
    def __init__(self):
        super().__init__()
        self.edits_made = []
        self.conversation_history = []
        self.tool_executions: List[Dict[str, Any]] = []  # {tool, duration_sec} for summary
    
    async def apply_changes(
        self, session: Session, instruction: str, llm: Optional[LLMClient] = None
    ) -> None:
        """
        Apply changes using agentic tool-based exploration.
        
        Args:
            session: Session dictionary containing session_id and session_path
            instruction: Natural language instruction from user
            llm: Optional LLM client (for testing); uses get_llm_client() if not provided.
        """
        llm = llm or get_llm_client()
        session_path = Path(session.path).joinpath("src")
        
        self.edits_made = []
        self.conversation_history = []
        self.tool_executions = []
        
        initial_prompt = self._build_initial_prompt(session, instruction, session_path)
        self.conversation_history.append({
            "role": "user",
            "content": initial_prompt
        })
        
        max_iterations = 25
        for iteration in range(max_iterations):
            logger.debug(f"Iteration {iteration + 1}/{max_iterations}")
            
            response = await llm.invoke(
                self._format_conversation(),
                session=session
            )
            try:
                parsed = self._parse_llm_response(response)
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {e}")
                break
            
            if parsed.get("done", False):
                logger.info(f"LLM finished after {iteration + 1} iterations")
                logger.info(f"Final message: {parsed.get('message', '')}")
                self.conversation_history.append({"role": "assistant", "content": response})
                break
            
            if "tool_calls" in parsed:
                tool_results = []
                for tool_call in parsed["tool_calls"]:
                    t0 = time.perf_counter()
                    result = self._execute_tool(
                        session_path,
                        tool_call["tool"],
                        tool_call["parameters"]
                    )
                    duration_sec = time.perf_counter() - t0
                    self.tool_executions.append({
                        "tool": tool_call["tool"],
                        "duration_sec": duration_sec,
                    })
                    tool_results.append({
                        "tool": tool_call["tool"],
                        "result": result
                    })
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": self._format_tool_results(tool_results)
                })
            else:
                logger.warning("LLM didn't call tools or mark as done")
                break
        
        if iteration == max_iterations - 1:
            logger.warning("Reached max iterations")

        self._log_workflow_summary()
        write_workflow_log(session.session_id, self._format_conversation())
    
    def _log_workflow_summary(self) -> None:
        """Log a one-time summary: tool counts and a visual timeline of tool durations."""
        if not self.tool_executions:
            logger.info("Workflow summary: no tools were used.")
            return

        total = len(self.tool_executions)
        total_sec = sum(e["duration_sec"] for e in self.tool_executions)
        by_tool: Dict[str, List[float]] = {}
        for e in self.tool_executions:
            by_tool.setdefault(e["tool"], []).append(e["duration_sec"])

        max_dur = max(e["duration_sec"] for e in self.tool_executions) or 1.0
        bar_width = 24
        lines = [
            "",
            "=== Workflow summary ===",
            f"Total tool calls: {total}  |  Total tool time: {total_sec:.2f}s",
            "",
            "Tool usage (count):",
        ]
        for tool_name in sorted(by_tool.keys()):
            count = len(by_tool[tool_name])
            lines.append(f"  {tool_name}: {count}")
        lines.append("")
        lines.append("Tool duration (visual, each bar = one call):")
        for tool_name in sorted(by_tool.keys()):
            durations = by_tool[tool_name]
            bars = []
            for d in durations:
                filled = max(1, round((d / max_dur) * bar_width))
                bars.append("█" * filled + "░" * (bar_width - filled))
            lines.append(f"  {tool_name}:")
            for i, bar in enumerate(bars):
                lines.append(f"    [{bar}] {durations[i]:.2f}s")
        lines.append("")
        logger.info("\n".join(lines))
    
    def _build_initial_prompt(self, session: Session, instruction: str, session_path: Path) -> str:
        """Build the initial prompt with tool descriptions and task."""
        
        # Get basic file tree
        file_tree = generate_file_tree(session_path, max_depth=3)
        tree_text = self._tree_to_simple_text(file_tree)

        previous_commands = session.user_questions[:-1] if len(session.user_questions) > 1 else []
        previous_block = ""
        if previous_commands:
            previous_block = "\n\nPREVIOUS USER COMMANDS (for context; current task is below):\n" + "\n".join(
                f"- {q}" for q in previous_commands
            ) + "\n"
        
        return f"""You are an expert code modification agent working on a React codebase.
{previous_block}
TASK: {instruction}

Use relative paths from the project root in all tools (e.g. src/App.jsx, components/Header.jsx).

INITIAL FILE TREE:
{tree_text}

AVAILABLE TOOLS:
You can use the following tools to explore and modify the codebase. Return your response as JSON.

1. list_files
   List files in a directory
   Parameters: {{"directory": "relative/path", "pattern": "*.jsx" (optional)}}

2. grep_code
   Search for text patterns in files
   Parameters: {{"pattern": "search text or regex", "file_pattern": "*.jsx" (optional), "context_lines": 2 (optional)}}

3. search_symbol
   Find where a function/variable is defined or used
   Parameters: {{"symbol": "functionName", "search_type": "definition" or "usage"}}

4. read_file_lines
   Read specific lines from a file
   Parameters: {{"file_path": "relative/path/to/file.jsx", "start_line": 1, "end_line": 50}}

5. get_file_structure
   Get outline of a file (imports and function signatures only, no implementation)
   Parameters: {{"file_path": "relative/path/to/file.jsx"}}

6. apply_edit
   Apply a targeted edit to a file (str_replace pattern - finds exact match and replaces)
   Parameters: {{"file_path": "path", "old_str": "exact string to replace", "new_str": "replacement"}}

RESPONSE FORMAT:
You must respond with valid JSON in one of two formats:

Format 1 - Using tools:
{{
  "thought": "explanation of what you're doing",
  "tool_calls": [
    {{"tool": "tool_name", "parameters": {{...}} }},
    {{"tool": "another_tool", "parameters": {{...}} }}
  ]
}}

Format 2 - When finished:
{{
  "done": true,
  "message": "summary of changes made"
}}

WORKFLOW SUGGESTIONS:
1. Start by exploring the codebase with list_files, grep_code, or get_file_structure
2. Read specific file sections with read_file_lines when you need to see implementation
3. Use search_symbol to find function definitions and usages
4. Once you understand the code, use apply_edit to make targeted changes
5. When all changes are complete, return {{"done": true}}

IMPORTANT:
- Be thorough but efficient - explore only what you need
- Use apply_edit for all modifications (don't suggest changes, make them)
- apply_edit uses exact string matching - make sure old_str matches exactly
- You can make multiple edits in one response
- When done, summarize what you changed

Begin by exploring the codebase to understand what needs to change."""

    def _format_conversation(self) -> str:
        """Format conversation history into a single prompt."""
        parts = []
        for msg in self.conversation_history:
            role_label = "USER" if msg["role"] == "user" else "ASSISTANT"
            parts.append(f"[{role_label}]\n{msg['content']}\n")
        return "\n".join(parts)
    
    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        """Format tool results for the next LLM call."""
        parts = ["TOOL RESULTS:\n"]
        for result in tool_results:
            parts.append(f"Tool: {result['tool']}")
            parts.append(f"Result:\n{result['result']}\n")
            parts.append("-" * 80)
        
        parts.append("\nContinue with your next action (use tools or mark as done).")
        return "\n".join(parts)
    
    def _parse_llm_response(self, response: str) -> Dict:
        text_to_parse = self._extract_json_from_response(response)
        try:
            return json.loads(text_to_parse)
        except json.JSONDecodeError as e:
            raise LLMParseError(
                f"Invalid JSON in LLM response: {e}",
                raw_response=text_to_parse[:500],
            ) from e

    def _execute_tool(self, session_path: Path, tool_name: str, parameters: Dict) -> str:
        logger.debug(f"Executing tool {tool_name} with parameters: {parameters}")
        try:
            if tool_name == "list_files":
                return self._tool_list_files(session_path, parameters)
            elif tool_name == "grep_code":
                return self._tool_grep_code(session_path, parameters)
            elif tool_name == "search_symbol":
                return self._tool_search_symbol(session_path, parameters)
            elif tool_name == "read_file_lines":
                return self._tool_read_file_lines(session_path, parameters)
            elif tool_name == "get_file_structure":
                return self._tool_get_file_structure(session_path, parameters)
            elif tool_name == "apply_edit":
                return self._tool_apply_edit(session_path, parameters)
            else:
                return f"ERROR: Unknown tool '{tool_name}'"
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return f"ERROR: Tool execution failed: {str(e)}"
    
    def _tool_list_files(self, session_path: Path, params: Dict) -> str:
        """List files in a directory."""
        directory = self._normalize_path(params.get("directory", "."))
        pattern = params.get("pattern")
        
        full_path = session_path / directory
        if not full_path.exists():
            return f"ERROR: Directory not found: {directory}"
        
        files = []
        for item in full_path.iterdir():
            if item.is_file():
                if pattern:
                    import fnmatch
                    if fnmatch.fnmatch(item.name, pattern):
                        files.append(f"  {item.name}")
                else:
                    files.append(f"  {item.name}")
            elif item.is_dir():
                files.append(f"  {item.name}/")
        
        if not files:
            return f"No files found in {directory}"
        
        return f"Files in {directory}:\n" + "\n".join(sorted(files))

    def _tool_grep_code(self, session_path: Path, params: Dict) -> str:
        pattern = params.get("pattern", "")
        file_pattern = self._normalize_file_pattern(params.get("file_pattern", "*"))
        context_lines = params.get("context_lines", 0)
        
        cmd = ["grep", "-r", "-n"]
        if context_lines > 0:
            cmd.extend(["-A", str(context_lines), "-B", str(context_lines)])
        cmd.extend(["--include", file_pattern])
        cmd.append(pattern)
        cmd.append(str(session_path))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = result.stdout
            
            if not output:
                return f"No matches found for pattern: {pattern}"
            
            session_prefix = str(session_path.resolve()) + os.sep
            lines = []
            for line in output.splitlines():
                if line.startswith(session_prefix):
                    line = line[len(session_prefix):]
                lines.append(line)
            output = "\n".join(lines)
            
            if len(output) > 5000:
                output = output[:5000] + "\n... (truncated, too many results)"
            
            return output
        except subprocess.TimeoutExpired:
            return "ERROR: Search timed out"
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def _tool_search_symbol(self, session_path: Path, params: Dict) -> str:
        """Find symbol definitions or usages."""
        symbol = params.get("symbol", "")
        search_type = params.get("search_type", "definition")
        
        if search_type == "definition":
            patterns = [
                f"function\\s+{symbol}",
                f"const\\s+{symbol}\\s*=",
                f"class\\s+{symbol}",
                f"export.*function\\s+{symbol}",
                f"export.*const\\s+{symbol}",
            ]
            pattern = "|".join(patterns)
        else:
            pattern = symbol
        
        return self._tool_grep_code(session_path, {
            "pattern": pattern,
            "file_pattern": "*.{js,jsx,ts,tsx}",
            "context_lines": 2
        })
    
    def _tool_read_file_lines(self, session_path: Path, params: Dict) -> str:
        """Read specific lines from a file."""
        file_path = self._normalize_path(params.get("file_path", ""))
        start_line = params.get("start_line", 1)
        end_line = params.get("end_line", -1)
        
        full_path = session_path / file_path
        if not full_path.exists():
            return f"ERROR: File not found: {file_path}"
        
        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()
            
            if end_line == -1:
                end_line = len(lines)
            
            selected_lines = lines[start_line - 1:end_line]
            
            numbered_lines = []
            for i, line in enumerate(selected_lines, start=start_line):
                numbered_lines.append(f"{i:4d} | {line.rstrip()}")
            
            return f"File: {file_path} (lines {start_line}-{end_line})\n" + "\n".join(numbered_lines)
        except Exception as e:
            return f"ERROR: Failed to read file: {str(e)}"
    
    def _tool_get_file_structure(self, session_path: Path, params: Dict) -> str:
        """Get outline of a file (imports, components, functions)."""
        file_path = self._normalize_path(params.get("file_path", ""))
        full_path = session_path / file_path
        
        if not full_path.exists():
            return f"ERROR: File not found: {file_path}"
        
        try:
            outline = self._get_file_outline(str(session_path), file_path)
            return self._format_file_structure_response(file_path, outline)
        except Exception as e:
            return f"ERROR: Failed to parse file: {str(e)}"
    
    def _tool_apply_edit(self, session_path: Path, params: Dict) -> str:
        """Apply a targeted edit using str_replace pattern."""
        file_path = self._normalize_path(params.get("file_path", ""))
        old_str = params.get("old_str", "")
        new_str = params.get("new_str", "")
        
        full_path = session_path / file_path
        if not full_path.exists():
            return f"ERROR: File not found: {file_path}"
        
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            if old_str not in content:
                return f"ERROR: Could not find exact match in {file_path}. Make sure old_str matches exactly including whitespace."
            
            count = content.count(old_str)
            if count > 1:
                return f"ERROR: Found {count} occurrences of old_str in {file_path}. Pattern must be unique."
            
            new_content = content.replace(old_str, new_str, 1)
            
            with open(full_path, 'w') as f:
                f.write(new_content)
            
            # Track edit
            self.edits_made.append({
                "file_path": file_path,
                "old_str": old_str,
                "new_str": new_str
            })
            
            logger.info(f"Applied edit to {file_path}")
            return f"SUCCESS: Applied edit to {file_path}"
            
        except Exception as e:
            return f"ERROR: Failed to apply edit: {str(e)}"
    
    def _tree_to_simple_text(self, node: dict, indent: int = 0) -> str:
        """Convert tree dict to simple indented text."""
        lines = []
        prefix = "  " * indent
        
        if node["type"] == "file":
            lines.append(f"{prefix}├── {node['name']}")
        else:
            lines.append(f"{prefix}├── {node['name']}/")
            for child in node.get("children", []):
                lines.append(self._tree_to_simple_text(child, indent + 1))
        
        return "\n".join(lines)
