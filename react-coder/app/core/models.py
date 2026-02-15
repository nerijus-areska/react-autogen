import io
from pathlib import Path
from typing import Optional
import subprocess
from pydantic import BaseModel


class Session(BaseModel):
    model_config = {"arbitrary_types_allowed": True} # otherwise subprocess Popen won't generate a schema

    session_id: str
    path: Path
    process: Optional[subprocess.Popen] = None
    log_file: Optional[io.TextIOWrapper] = None
    input_tokens: int = 0
    output_tokens: int = 0
    workflow: Optional[str] = None
