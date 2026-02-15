import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.models import Session
from app.workflows.explorative_modification.workflow import ExplorativeModificationWorkflow


def _make_session(tmpdir: Path, with_src: bool = True) -> Session:
    """Create a session with optional src directory."""
    if with_src:
        (tmpdir / "src").mkdir(exist_ok=True)
    return Session(session_id="test-session", path=tmpdir)


@pytest.fixture
def patch_workflow_log():
    """Avoid writing to dev_blog/logs during tests."""
    with patch("app.workflows.explorative_modification.workflow.write_workflow_log"):
        yield


@pytest.mark.asyncio
async def test_apply_changes_exits_when_llm_returns_done(patch_workflow_log):
    """When LLM returns done=true on first call, workflow exits after one invoke and leaves state consistent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session = _make_session(Path(tmpdir))
        mock_llm = AsyncMock()
        mock_llm.invoke.return_value = '{"done": true, "message": "ok"}'

        workflow = ExplorativeModificationWorkflow()
        await workflow.apply_changes(session, "do nothing", llm=mock_llm)

        mock_llm.invoke.assert_called_once()
        assert len(workflow.conversation_history) == 2  # user prompt + assistant done
        assert workflow.conversation_history[0]["role"] == "user"
        assert workflow.conversation_history[1]["role"] == "assistant"
        assert workflow.edits_made == []
        assert workflow.tool_executions == []


@pytest.mark.asyncio
async def test_apply_changes_executes_tools_then_exits(patch_workflow_log):
    """When LLM returns tool_calls then done, tools run and invoke is called twice."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session = _make_session(Path(tmpdir))
        mock_llm = AsyncMock()
        mock_llm.invoke.side_effect = [
            # First call: use list_files
            '{"thought": "listing", "tool_calls": [{"tool": "list_files", "parameters": {"directory": "."}}]}',
            # Second call: done
            '{"done": true, "message": "listed"}',
        ]

        workflow = ExplorativeModificationWorkflow()
        await workflow.apply_changes(session, "explore", llm=mock_llm)

        assert mock_llm.invoke.call_count == 2
        assert len(workflow.tool_executions) == 1
        assert workflow.tool_executions[0]["tool"] == "list_files"
        assert len(workflow.conversation_history) == 4  # user, assistant, user (tool results), assistant
        assert workflow.edits_made == []


@pytest.mark.asyncio
async def test_apply_changes_apply_edit_recorded(patch_workflow_log):
    """When LLM uses apply_edit, the edit is applied on disk and recorded in edits_made."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "src"
        src.mkdir()
        (src / "App.jsx").write_text("const x = 1;\nconst y = 2;\n")
        session = Session(session_id="test-session", path=tmpdir)

        mock_llm = AsyncMock()
        mock_llm.invoke.side_effect = [
            '{"thought": "edit", "tool_calls": [{"tool": "apply_edit", "parameters": {"file_path": "App.jsx", "old_str": "const x = 1;", "new_str": "const x = 42;"}}]}',
            '{"done": true, "message": "updated"}',
        ]

        workflow = ExplorativeModificationWorkflow()
        await workflow.apply_changes(session, "change x", llm=mock_llm)

        assert mock_llm.invoke.call_count == 2
        assert len(workflow.edits_made) == 1
        assert workflow.edits_made[0]["file_path"] == "App.jsx"
        assert workflow.edits_made[0]["old_str"] == "const x = 1;"
        assert workflow.edits_made[0]["new_str"] == "const x = 42;"
        assert (src / "App.jsx").read_text() == "const x = 42;\nconst y = 2;\n"


@pytest.mark.asyncio
async def test_apply_changes_handles_invalid_json_gracefully(patch_workflow_log):
    """When LLM returns invalid JSON, workflow breaks without crashing and does not call invoke again."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session = _make_session(Path(tmpdir))
        mock_llm = AsyncMock()
        mock_llm.invoke.return_value = "This is not JSON at all."

        workflow = ExplorativeModificationWorkflow()
        await workflow.apply_changes(session, "do something", llm=mock_llm)

        mock_llm.invoke.assert_called_once()
        # Conversation has initial user message; parsing failed so we break without adding assistant
        assert len(workflow.conversation_history) == 1
        assert workflow.tool_executions == []


@pytest.mark.asyncio
async def test_apply_changes_uses_injected_llm(patch_workflow_log):
    """When llm is passed, get_llm_client is not used; when not passed, it is used."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session = _make_session(Path(tmpdir))
        mock_llm = AsyncMock()
        mock_llm.invoke.return_value = '{"done": true, "message": "ok"}'

        with patch("app.workflows.explorative_modification.workflow.get_llm_client") as get_client:
            workflow = ExplorativeModificationWorkflow()
            await workflow.apply_changes(session, "do nothing", llm=mock_llm)
            get_client.assert_not_called()

        with patch("app.workflows.explorative_modification.workflow.get_llm_client") as get_client:
            get_client.return_value = AsyncMock(invoke=AsyncMock(return_value='{"done": true}'))
            workflow2 = ExplorativeModificationWorkflow()
            await workflow2.apply_changes(session, "do nothing")  # no llm=
            get_client.assert_called_once()
