import sys
import time
import requests
import json
import argparse
import shlex
from pathlib import Path

# --- UI Libraries ---
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

# --- Configuration ---
API_URL = "http://localhost:8000/api/v1/editor"
SESSION_FILE = Path(".vibe_session")
HISTORY_FILE = Path(".vibe_history")

# Price per 1M tokens: (input, output)
MODEL_PRICING = {
    "gpt-5-mini": (0.25, 2.00),
}

console = Console()

# --- Custom Argument Parser for the REPL ---
class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # Prevent argparse from killing the shell on error
        raise ValueError(message)

class VibeClient:
    def __init__(self):
        self.session_id = None
        self.project_name = None
        self.model = None

        # Setup Prompt Toolkit with history
        self.prompter = PromptSession(
            history=FileHistory(str(HISTORY_FILE)),
            style=Style.from_dict({
                'prompt': '#00ffff bold',  # Cyan
                'project': '#00ff00',      # Green
            })
        )
        
        self.load_state()

    def load_state(self):
        """Try to load an existing session from disk."""
        if SESSION_FILE.exists():
            try:
                data = json.loads(SESSION_FILE.read_text())
                self.session_id = data.get("session_id")
                self.project_name = data.get("project")
                self.model = data.get("model")
                console.print(f"[dim]🔄 Restored session for '{self.project_name}'[/]")
            except:
                pass

    def save_state(self):
        if self.session_id:
            SESSION_FILE.write_text(json.dumps({
                "session_id": self.session_id,
                "project": self.project_name,
                "model": self.model
            }))

    def clear_state(self):
        self.session_id = None
        self.project_name = None
        self.model = None
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    def print_help(self):
        console.print(Panel(
            "[bold]Available Commands:[/]\n"
            "  [cyan]/init <project> [--run] [--port 3000] [--workflow TYPE][/]\n"
            "      Start a new session. Flags:\n"
            "      --run, -r          Start the React app\n"
            "      --port, -p         Specify port (default: 3000)\n"
            "      --workflow, -w     simple_modification | explorative_modification\n\n"
            "  [cyan]/list[/]   List available projects\n"
            "  [cyan]/stop[/]   Stop session and cleanup\n"
            "  [cyan]/clear[/]  Clear screen\n"
            "  [cyan]/exit[/]   Quit CLI",
            title="🤖 Vibe Coding Help",
            border_style="blue",
            expand=False
        ))

    def do_init(self, args_list):
        # 1. Check if session exists
        if self.session_id:
            console.print(f"[yellow]⚠️  Session '{self.project_name}' is already active. Run /stop first.[/]")
            return

        # 2. Parse Arguments using argparse logic
        parser = ArgumentParser(description="Init Command", add_help=False)
        parser.add_argument("project_name", help="Name of the project folder")
        parser.add_argument("--run", "-r", action="store_true", help="Run the app")
        parser.add_argument("--port", "-p", type=int, default=3000, help="Port to run on")
        parser.add_argument("--workflow", "-w", choices=["simple_modification", "explorative_modification"],
                            default="simple_modification", help="Workflow type")

        try:
            args = parser.parse_args(args_list)
        except ValueError as e:
            console.print(f"[red]❌ Error:[/]{str(e)}")
            return

        # 3. Call API
        with console.status(f"[bold green]🚀 Initializing '{args.project_name}'..."):
            try:
                payload = {
                    "project_name": args.project_name,
                    "run_app": args.run,
                    "port": args.port,
                    "workflow": args.workflow
                }
                res = requests.post(f"{API_URL}/init", json=payload)
                res.raise_for_status()
                data = res.json()
                
                self.session_id = data["session_id"]
                self.project_name = args.project_name
                self.model = data.get("model_used")
                self.save_state()

                # 4. Success Output
                msg = f"[bold green]✅ Session Started![/]\n"
                msg += f"📂 Project: [cyan]{self.project_name}[/]\n"
                msg += f"🤖 Model: [magenta]{self.model}[/]\n"
                msg += f"🆔 ID: [dim]{self.session_id}[/]"
                
                if data.get("app_url"):
                    # RICH LINK FORMAT: [link=URL]TEXT[/link]
                    url = data['app_url']
                    msg += f"\n\n🔗 [bold underline white on blue link={url}] Click here to open App: {url} [/]"
                
                console.print(Panel(msg, title="System Ready", border_style="green"))

            except requests.exceptions.ConnectionError:
                console.print("[bold red]❌ Error:[/] API server is not running at localhost:8000")
            except Exception as e:
                console.print(f"[bold red]❌ Init Failed:[/] {e}")

    def do_stop(self):
        if not self.session_id:
            console.print("[yellow]⚠️  No active session.[/]")
            return

        with console.status("[bold red]🛑 Stopping session..."):
            try:
                requests.post(f"{API_URL}/stop", json={"session_id": self.session_id})
            except:
                pass 
            
            self.clear_state()
            console.print("[bold green]✔ Session ended.[/]")

    def do_list(self):
        excluded = {"react-coder", "react-coder-client", ".git"}
        projects_dir = Path(__file__).resolve().parent.parent
        projects = sorted(
            p.name for p in projects_dir.iterdir()
            if p.is_dir() and p.name not in excluded
        )

        if not projects:
            console.print("[yellow]No projects found.[/]")
            return

        listing = "\n".join(f"  [cyan]{i}.[/] {name}" for i, name in enumerate(projects, 1))
        console.print(Panel(
            f"[bold]Projects in [dim]{projects_dir}[/]:[/]\n\n{listing}",
            title="📂 Available Projects",
            border_style="blue",
            expand=False
        ))

    def do_chat(self, message):
        if not self.session_id:
            console.print("[bold red]❌ No active session.[/] Run [bold cyan]/init <project>[/] first.")
            return

        with console.status("[bold blue]🧠 AI is thinking..."):
            try:
                start_time = time.time()
                payload = {"session_id": self.session_id, "instruction": message}
                res = requests.post(f"{API_URL}/chat", json=payload)
                elapsed = time.time() - start_time
                
                if res.status_code == 400:
                    console.print("[bold red]❌ Session expired.[/] Please re-init.")
                    self.clear_state()
                    return
                
                res.raise_for_status()
                data = res.json()

                input_tok = data.get("input_tokens", 0)
                output_tok = data.get("output_tokens", 0)
                workflow = data.get("workflow", "unknown")

                # Estimate cost
                pricing = MODEL_PRICING.get(self.model)
                if pricing:
                    cost = (input_tok * pricing[0] + output_tok * pricing[1]) / 1_000_000
                    cost_str = f"  [bold yellow]💲 Est. Cost (no cache):[/] [bold bright_green]${cost:.4f}[/]"
                else:
                    cost_str = ""

                console.print(
                    f"\n[bold yellow]⚡ Session Input Tokens:[/] [bright_cyan]{input_tok:,}[/]"
                    f"  [bold yellow]⚡ Session Output Tokens:[/] [bright_magenta]{output_tok:,}[/]"
                    f"  [bold yellow]🔧 Workflow:[/] [yellow]{workflow}[/]"
                    f"{cost_str}"
                )

                changes = data.get("changes", [])

                if not changes:
                    console.print("[dim]🤖 AI suggests no code changes.[/]")
                else:
                    for change in changes:
                        console.print(f"\n📄 [bold underline]{change['filename']}[/]")
                        syntax = Syntax(change["diff"], "diff", theme="monokai", line_numbers=True)
                        console.print(syntax)
                    
                    console.print(f"\n[bold green]✅ Applied changes to {len(changes)} file(s).[/]")

                console.print(f"\n[bold bright_white on blue] ⏱  Request took {elapsed:.1f}s [/]")

            except Exception as e:
                console.print(f"[bold red]❌ Error:[/] {e}")

    def start(self):
        console.clear()
        console.print(Panel("[bold magenta]Welcome to Vibe Coder 2.0[/]\nType [cyan]/help[/] for commands.", subtitle="Pro Mode"))

        while True:
            try:
                # Dynamic prompt string
                if self.project_name:
                    model_tag = f"/{self.model}" if self.model else ""
                    p_text = f"({self.project_name}{model_tag})"
                    p_class = "class:project"
                else:
                    p_text = "(no-project)"
                    p_class = "class:prompt"

                # Prompt Toolkit handles Up/Down arrow history automatically
                user_input = self.prompter.prompt(
                    [
                        (p_class, f"{p_text} "),
                        ('class:prompt', "> ")
                    ]
                ).strip()

                if not user_input:
                    continue

                # Parse Command vs Chat
                if user_input.startswith("/"):
                    # Use shlex to handle quotes: /init "my project"
                    parts = shlex.split(user_input)
                    cmd = parts[0].lower()
                    args = parts[1:]

                    if cmd == "/exit":
                        console.print("[dim]Goodbye![/]")
                        sys.exit(0)
                    elif cmd == "/help":
                        self.print_help()
                    elif cmd == "/clear":
                        console.clear()
                    elif cmd == "/init":
                        self.do_init(args)
                    elif cmd == "/stop":
                        self.do_stop()
                    elif cmd == "/list":
                        self.do_list()
                    else:
                        console.print(f"[red]Unknown command: {cmd}[/]")
                else:
                    self.do_chat(user_input)

            except KeyboardInterrupt:
                continue # CTRL+C just clears line, doesn't kill app
            except EOFError:
                break # CTRL+D exits

if __name__ == "__main__":
    client = VibeClient()
    client.start()
    