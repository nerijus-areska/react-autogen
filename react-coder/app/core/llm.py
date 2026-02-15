import hashlib
from pathlib import Path

from app.core.models import Session
from langchain_openai import ChatOpenAI
from typing import Optional

from app.core.config import settings

# Project root (react-coder directory)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOGS_DIR = _PROJECT_ROOT / "dev_blog" / "logs" 
import logging

logger = logging.getLogger(__name__)

def _chatlog_path(session_id: str) -> Path:
    """Path to this session's chat log file in logs/ (4-char hash of session_id)."""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = hashlib.sha256(session_id.encode()).hexdigest()[:4]
    return _LOGS_DIR / f"{prefix}_chatlog.txt"


def _workflow_log_path(session_id: str) -> Path:
    """Path to this session's workflow log file in logs/ (same 4-char hash, _workflow suffix)."""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = hashlib.sha256(session_id.encode()).hexdigest()[:4]
    return _LOGS_DIR / f"{prefix}_workflow.txt"


def write_workflow_log(session_id: str, content: str) -> None:
    """Write the formatted conversation history once to the session's workflow log (explorative workflow)."""
    log_path = _workflow_log_path(session_id)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(content)


def _append_exchange(prompt: str, response: str, session_id: str) -> None:
    """Append a single request/response exchange to the session's chat log (no history)."""
    log_path = _chatlog_path(session_id)
    # Make escaped newlines/tabs in response readable in the log (e.g. JSON with "\\n")
    response_for_log = response.replace("\\n", "\n").replace("\\t", "\t")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n---\n")
        f.write("REQUEST:\n")
        f.write(prompt)
        f.write("\n\nRESPONSE:\n")
        f.write(response_for_log)
        f.write("\n")


def _usage_from_response(response) -> tuple[int, int]:
    """
    Extract (input_tokens, output_tokens) from a LangChain AIMessage.

    Supports usage_metadata (input_tokens/output_tokens) and response_metadata
    token_usage (prompt_tokens/completion_tokens) for compatibility.
    """
    input_tokens, output_tokens = 0, 0
    um = getattr(response, "usage_metadata", None)
    logger.info(f"Usage metadata: {um}")
    logger.info(f"Response metadata: {getattr(response, "response_metadata", None)}")
    logger.info(f"Token usage: {getattr(response, "token_usage", None)}")
    logger.info(f"Usage: {getattr(response, "usage", None)}")
    logger.info(f"Usage metadata: {getattr(response, "usage_metadata", None)}")
    logger.info(f"Usage metadata: {getattr(response, "token_usage", None)}")
    if um is not None:
        if isinstance(um, dict):
            input_tokens = um.get("input_tokens", 0) or 0
            output_tokens = um.get("output_tokens", 0) or 0
        else:
            input_tokens = getattr(um, "input_tokens", 0) or 0
            output_tokens = getattr(um, "output_tokens", 0) or 0
    if input_tokens == 0 and output_tokens == 0:
        rm = getattr(response, "response_metadata", None) or {}
        usage = rm.get("token_usage") or rm.get("usage") or {}
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
    return (int(input_tokens), int(output_tokens))


class LLMClient:
    """
    Wrapper around LangChain's ChatOpenAI for consistent LLM interactions.
    
    Supports both local or cloud providers through the same OpenAI-compatible API.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize LLM client.
        
        Args:
            base_url: API base URL (e.g., "http://localhost:1234/v1" for LM Studio)
            api_key: API key (use "not-needed" for LM Studio)
            model: Model name
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
        """
        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        
        # Initialize LangChain ChatOpenAI
        self.client = ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
    
    async def invoke(self, prompt: str, session: Session) -> str:
        """
        Send a prompt to the LLM and get a response.

        Args:
            prompt: The prompt text
            session: Session to log the exchange and accumulate token usage

        Returns:
            LLM response as string
        """
        response = await self.client.ainvoke(prompt)
        content = response.content
        inc_in, inc_out = _usage_from_response(response)
        session.input_tokens += inc_in
        session.output_tokens += inc_out
        _append_exchange(prompt, content, session.session_id)
        return content
    
    def invoke_sync(self, prompt: str, session: Session) -> str:
        """
        Synchronous version of invoke.

        Args:
            prompt: The prompt text
            session: Session to log the exchange and accumulate token usage

        Returns:
            LLM response as string
        """
        response = self.client.invoke(prompt)
        content = response.content
        inc_in, inc_out = _usage_from_response(response)
        session.input_tokens += inc_in
        session.output_tokens += inc_out
        _append_exchange(prompt, content, session.session_id)
        return content
    
    def with_temperature(self, temperature: float) -> 'LLMClient':
        """
        Create a new client instance with different temperature.
        
        Useful for different tasks (creative vs deterministic).
        
        Args:
            temperature: New temperature value
            
        Returns:
            New LLMClient instance
        """
        return LLMClient(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            temperature=temperature,
            max_tokens=self.max_tokens,
        )
    
    def with_model(self, model: str) -> 'LLMClient':
        """
        Create a new client instance with different model.
        
        Useful for using different models for different tasks
        (e.g., fast model for routing, powerful model for code generation).
        
        Args:
            model: New model name
            
        Returns:
            New LLMClient instance
        """
        return LLMClient(
            base_url=self.base_url,
            api_key=self.api_key,
            model=model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


# Singleton instance for easy import
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get the default LLM client instance.
    
    Uses settings from config. Lazy initialization - only creates client
    when first requested.
    
    Returns:
        LLMClient instance configured from settings
    """
    global _default_client
    
    if _default_client is None:
        _default_client = LLMClient()
    
    return _default_client


def get_router_llm_client() -> LLMClient:
    """
    Get an LLM client optimized for routing decisions.
    
    May use a faster/cheaper model than the main workflow model.
    
    Returns:
        LLMClient instance for routing
    """
    # If router model is specified, use it; otherwise use default
    if settings.ROUTER_LLM_MODEL and settings.ROUTER_LLM_MODEL != settings.LLM_MODEL:
        return LLMClient(
            model=settings.ROUTER_LLM_MODEL,
            temperature=0.0,  # Routing should be deterministic
        )
    
    return get_llm_client().with_temperature(0.0)


def reset_client():
    """
    Reset the default client singleton.
    
    Useful for testing or when configuration changes.
    """
    global _default_client
    _default_client = None