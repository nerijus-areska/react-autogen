# React Autogen

AI-powered code modification system for React projects. Describe what you want in natural language, and the AI modifies your Vite/React/TailwindCSS codebase — with live preview and git-tracked diffs.

📝 [Development Blog](react-coder/dev_blog/blog.md)

## How It Works

1. **Initialize** a session pointing at one of your React projects
2. **Describe** changes in plain English (e.g. "Change the Add Todo button color to blue")
3. The server copies your project to a sandboxed temp directory, runs an AI workflow that reads, understands, and edits the code
4. **Review** the git diffs returned to your terminal — changes are applied to the sandbox, not your original project

The system supports two workflow strategies that the AI can choose between automatically:

| Workflow | How it works | Best for |
|----------|-------------|----------|
| **Simple Modification** | Scans file tree → identifies relevant files → rewrites them in full | Small, targeted changes |
| **Explorative Modification** | Agentic loop with tools (grep, read, search, edit) — up to 25 iterations | Complex changes requiring codebase understanding |

## Project Structure

```
├── react-coder/            # FastAPI backend server
│   ├── app/
│   │   ├── main.py         # App factory & exception handlers
│   │   ├── api/            # REST endpoints (init, chat, stop)
│   │   ├── core/           # Config, LLM client, file operations, models
│   │   ├── services/       # Session management (copy, git, npm, diffs)
│   │   └── workflows/      # AI workflow implementations
│   └── tests/
├── react-coder-client/     # Interactive CLI client
│   └── client.py
└── <project-dirs>/         # Target Template React/Vite projects (e.g. 1-todo-app)
```

## Prerequisites

- Python 3.12+
- Node.js (for running target React projects)
- Access to an OpenAI-compatible LLM API (OpenAI, LM Studio, etc.)

## Setup

### 1. Backend

```bash
cd react-coder
python3.12 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn langchain langchain-openai pydantic-settings python-dotenv httpx pyyaml orjson
pip install -r requirements-dev.txt  # pytest, pytest-asyncio
```

Create a `.env` file in `react-coder/`:

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=64512
ROUTER_LLM_MODEL=          # optional: cheaper model for workflow routing
```

### 2. Client

```bash
cd react-coder-client
pip install requests rich prompt-toolkit
```

## Usage

**Start the server:**

```bash
cd react-coder
source venv/bin/activate
./start.sh
```

**In another terminal, start the client:**

```bash
cd react-coder-client
python client.py
```

**Client commands:**

```
/init <project> [--run] [--port 3000] [--workflow simple_modification|explorative_modification]
/list              List available projects
/stop              Stop current session
/clear             Clear screen
/exit              Quit

<any text>         Send instruction to the AI
```

**Example session:**

```
> /list
> /init 1-todo-app --run
> add a button to clear all completed todos
> make the todo items animate when added
> /stop
```

With `--run`, the server starts `npm run dev` in the sandbox so you can see changes live at `http://localhost:<port>`.

## Adding Projects

Place any Vite/React project directory in the repository root. It will appear in `/list` and can be used with `/init`. The project should have:

- A `src/` directory with your React source code
- A `package.json` with a `dev` script (for `--run` mode)
- `node_modules/` installed (symlinked into the sandbox to save space)

## API

The server exposes a REST API at `http://localhost:8000/api/v1/editor`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/init` | POST | Create a session — copies project, optionally runs dev server |
| `/chat` | POST | Send an instruction — returns file diffs |
| `/stop` | POST | Terminate session and clean up |
| `/health` | GET | Health check (at root: `http://localhost:8000/health`) |

## Running Tests

```bash
cd react-coder
source venv/bin/activate
pytest tests/
pytest tests/unit/workflows/explorative_modification/test_workflow.py -v
```