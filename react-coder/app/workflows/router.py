"""
LLM-based workflow router: selects a workflow by name when the client does not provide one.
"""
import json
import logging
from app.core.llm import get_llm_client
from app.core.models import Session
from app.workflows.registry import WorkflowRegistry

logger = logging.getLogger(__name__)

DEFAULT_WORKFLOW = "simple_modification"


async def select_workflow(instruction: str, session: Session) -> str:
    """
    Use the LLM to choose a workflow based on the user instruction.
    Returns a registered workflow name. Falls back to DEFAULT_WORKFLOW on parse error or unknown name.
    """
    options = WorkflowRegistry.list_workflow_options()
    if not options:
        logger.warning("No workflows registered; using default")
        return DEFAULT_WORKFLOW

    valid_names = [opt["name"] for opt in options]
    options_text = "\n".join(
        f"- {opt['name']}: {opt['description']} (complexity: {opt['complexity_level']})"
        for opt in options
    )

    prompt = f"""You are a router for a code-editing system. Given the user's instruction, choose exactly one workflow.

User instruction: "{instruction}"

Available workflows:
{options_text}

Respond with a JSON object only, no other text:
{{"workflow": "<name>", "reason": "<one short sentence>"}}

Use exactly one of these workflow names: {', '.join(valid_names)}."""

    llm = get_llm_client()
    try:
        response = await llm.invoke(prompt, session=session)
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        name = parsed.get("workflow")
        if name and name in valid_names:
            logger.info(f"Router selected workflow={name}, reason={parsed.get('reason', '')}")
            return name
        logger.warning(f"Router returned unknown or missing workflow name: {name!r}; using default")
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Router LLM response was not valid JSON: {e}; using default")
    except Exception as e:
        logger.warning(f"Router failed: {e}; using default")

    return DEFAULT_WORKFLOW
