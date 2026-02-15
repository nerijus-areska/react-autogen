import os
import re
import shutil
import socket
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from app.core.models import Session
from app.workflows.registry import WorkflowRegistry
from app.workflows.router import select_workflow

# Redis incoming next week
_active_sessions: Dict[str, Session] = {}

logger = logging.getLogger(__name__)

class EditorService:
    def __init__(self):
        self.base_dir = Path(os.getcwd())
        self.projects_root = self.base_dir.parent  # Sister directories for the projects
        self.temp_root = self.base_dir / "temp_sessions"
        self.temp_root.mkdir(exist_ok=True)

    async def initialize_session(
        self,
        project_name: str,
        run_app: bool = False,
        port: int = 3001,
        workflow: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a sandboxed environment for the requested project.
        """
        source_path = self.projects_root / project_name
        
        if not source_path.exists():
            source_path = self.base_dir / project_name
            if not source_path.exists():
                raise FileNotFoundError(f"Project '{project_name}' not found at {source_path}")

        if run_app and self._is_port_in_use(port):
            return {"session_id": "not started", "app_url": f"{port} port taken"}

        session_id = str(uuid.uuid4())
        session_path = self.temp_root / session_id

        shutil.copytree(
            source_path, 
            session_path, 
            ignore=shutil.ignore_patterns("node_modules", ".git", "dist", "build")
        )

        # Symlink node_modules, it would be stupid to copy those
        src_node_modules = source_path / "node_modules"
        if src_node_modules.exists():
            os.symlink(src_node_modules, session_path / "node_modules")

        self._run_command(["git", "init"], cwd=session_path)
        self._run_command(["git", "config", "user.email", "react-coder@hostinger.com"], cwd=session_path)
        self._run_command(["git", "config", "user.name", "React Coder"], cwd=session_path)
        self._run_command(["git", "add", "."], cwd=session_path)
        self._run_command(["git", "commit", "-m", "Initial state"], cwd=session_path)

        app_url = None
        proc = None
        if run_app:
            app_url = f"http://localhost:{port}"
            log_file = open(session_path / "server.log", "w")
            proc = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", str(port)],
                cwd=session_path,
                stdout=log_file,
                stderr=log_file,
                env={**os.environ, **({"BROWSER": "none"})}
            )

        _active_sessions[session_id] = Session(
            session_id=session_id,
            path=session_path,
            process=proc,
            log_file=log_file if run_app else None,
            workflow=workflow,
        )

        return {"session_id": session_id, "app_url": app_url}

    async def process_instruction(
        self,
        session_id: str,
        instruction: str,
    ) -> tuple:
        """
        Orchestrates the AI editing process.
        """
        if session_id not in _active_sessions:
            raise ValueError("Invalid or expired session ID")

        session = _active_sessions[session_id]
        session_path = session.path

        await self._apply_ai_changes(
            session,
            instruction,
            workflow_name=session.workflow,
        )

        diff_output = self._run_command(["git", "diff", "HEAD"], cwd=session_path)

        changes = self._parse_git_diff(diff_output)

        if changes:
            self._run_command(["git", "add", "."], cwd=session_path)
            self._run_command(["git", "commit", "-m", f"AI: {instruction}"], cwd=session_path)

        workflow_used = session.workflow or "simple_modification"
        return changes, session.input_tokens, session.output_tokens, workflow_used
    
    async def _apply_ai_changes(
        self,
        session: Session,
        instruction: str,
        workflow_name: Optional[str] = None,
    ):
        if workflow_name:
            selected = workflow_name
        else:
            selected = await select_workflow(instruction, session)
        session.workflow = selected
        workflow = WorkflowRegistry.get(selected)
        await workflow.apply_changes(session, instruction)

    async def cleanup_session(self, session_id: str):
        if session_id in _active_sessions:
            session = _active_sessions[session_id]
            logger.info(f"Cleaning up session {session_id}, process: {session['process']}")

            if session["process"]:
                session["process"].terminate()
                try:
                    session["process"].wait(timeout=5)
                except subprocess.TimeoutExpired:
                    session["process"].kill()
                
                if session["log_file"]:
                    session["log_file"].close()

            if session["path"].exists(): # Does this work?
                shutil.rmtree(session["path"])
            
            del _active_sessions[session_id]

    def _is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    def _run_command(self, command: List[str], cwd: Path) -> str:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            print(f"Command failed: {command}\nStderr: {result.stderr}")
        return result.stdout

    def _parse_git_diff(self, diff_text: str) -> List[Dict[str, str]]:
        """
        Parses raw 'git diff' output into the required JSON structure.
        Structure: [{'filename': '...', 'diff': '...'}]
        """
        changes = []
        raw_files = re.split(r'(?=diff --git )', diff_text)

        for raw_chunk in raw_files:
            if not raw_chunk.strip():
                continue

            match = re.search(r'\+\+\+ b/(.*)', raw_chunk)
            if not match:
                match = re.search(r'--- a/(.*)', raw_chunk)
            
            if match:
                filename = match.group(1)
                changes.append({
                    "filename": filename,
                    "diff": raw_chunk.strip()
                })
        
        return changes