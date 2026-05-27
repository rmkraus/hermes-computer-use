# Hermes Computer Use

Ubuntu desktop automation agent — powered by [LangChain DeepAgents](https://github.com/langchain-ai/deepagents), served as an **MCP server** and an **OpenAI-compatible API** on a single port.

```
┌────────────────────────────────────────────────────────────────┐
│  Any MCP Client                  Any OpenAI client             │
│  (Hermes, Claude Desktop,        (curl, LangChain, Hermes,     │
│   Cursor, VS Code, ...)           Python openai SDK, ...)      │
└────────────┬───────────────────────────┬───────────────────────┘
             │  MCP  /mcp                │  HTTP  /v1/chat/completions
             ▼                           ▼
┌────────────────────────────────────────────────────────────────┐
│               hermes-computer-use server (port 8000)           │
│  ┌──────────────────┐   ┌────────────────────────────────────┐ │
│  │  FastMCP layer   │   │  FastAPI OpenAI-compat layer       │ │
│  │  run_computer_use│   │  POST /v1/chat/completions         │ │
│  └────────┬─────────┘   └───────────────┬────────────────────┘ │
│           └────────────────┬────────────┘                      │
│                            ▼                                    │
│           ┌─────────────────────────────┐                      │
│           │  DeepAgent (LangGraph graph) │                      │
│           │  create_deep_agent(model,    │                      │
│           │    tools=[...])              │                      │
│           └─────────────┬───────────────┘                      │
│                         ▼                                       │
│           ┌─────────────────────────────┐                      │
│           │  Computer-Use Tools          │                      │
│           │  take_screenshot  click      │                      │
│           │  type_text        key_press  │                      │
│           │  scroll           move_mouse │                      │
│           │  run_command      zoom_region│                      │
│           │  list_windows  focus_window  │                      │
│           │  get_screen_info             │                      │
│           └─────────────────────────────┘                      │
│                         ▼                                       │
│           ┌─────────────────────────────┐                      │
│           │  Xvfb virtual display        │                      │
│           │  Ubuntu 24.04 desktop        │                      │
│           └─────────────────────────────┘                      │
└────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Docker (recommended)

```bash
# Copy and fill in your LLM API key
cp .env.example .env
# OPENAI_API_KEY=sk-...         (for gpt-4o)
# NVIDIA_API_KEY=nvapi-...      (for NVIDIA NIM models)
# COMPUTER_USE_MODEL=openai:gpt-4o

docker compose up --build
```

The server starts on **port 8002** (maps to 8000 inside the container).

### Bare metal

```bash
# Install system deps
sudo apt-get install -y xvfb scrot xdotool xterm

# Install Python package
pip install -e ".[all]"

# Start the server
COMPUTER_USE_MODEL=openai:gpt-4o \
OPENAI_API_KEY=sk-... \
python -m hermes_computer_use.server --port 8000
```

## MCP Integration

Add to your MCP client config (e.g. Claude Desktop `config.json`):

```json
{
  "mcpServers": {
    "computer-use": {
      "url": "http://localhost:8002/mcp"
    }
  }
}
```

Or for Hermes Agent (`~/.hermes/config.yaml`):

```yaml
mcp_servers:
  - name: computer-use
    url: http://localhost:8002/mcp
```

The server exposes **one MCP tool**:

| Tool | Description |
|------|-------------|
| `run_computer_use` | Give the agent a plain-English goal. It screenshots, clicks, types, and runs commands to complete it. |

## OpenAI API Integration

Point any OpenAI client at the server:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8002/v1",
    api_key="not-needed",
)

response = client.chat.completions.create(
    model="hermes-computer-use",
    messages=[{"role": "user", "content": "Open Firefox and go to example.com"}],
)
print(response.choices[0].message.content)
```

Or with curl:

```bash
curl http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes-computer-use","messages":[{"role":"user","content":"Take a screenshot"}]}'
```

## Available Models

The agent works with any OpenAI-compatible LLM. Set `COMPUTER_USE_MODEL` to:

| Model string | Description |
|---|---|
| `openai:gpt-4o` | GPT-4o (default) |
| `openai:gpt-4o-mini` | Faster / cheaper |
| `nvidia:meta/llama-3.1-70b-instruct` | NVIDIA NIM |
| `nvidia:nvidia/llama-3.2-90b-vision-instruct` | NVIDIA NIM with vision |
| Any `langchain` init_chat_model string | See [LangChain docs](https://python.langchain.com/docs/how_to/chat_models_universal_init/) |

## Tool Catalog

| Tool | What it does |
|------|-------------|
| `take_screenshot` | Full-screen screenshot → base64 PNG |
| `zoom_region` | Crop + upscale a region for reading small text |
| `click` | Mouse click (left/right/middle, single/double) |
| `move_mouse` | Move cursor without clicking |
| `scroll` | Scroll wheel at position |
| `type_text` | Type a string (blocked on dangerous patterns) |
| `key_press` | Single key or hotkey combo (e.g. `ctrl+c`) |
| `list_windows` | List all visible windows |
| `focus_window` | Bring window to foreground |
| `run_command` | Run shell command via `bash -c` |
| `get_screen_info` | Screen resolution and display server type |

## Safety

The `SafetyChecker` runs before every action:

- **Text/command blocking** — rejects `rm -rf`, `DROP TABLE`, fork bombs, and credential patterns
- **Hotkey blocking** — rejects `Alt+F4`, `Ctrl+Alt+Delete`, and other system-critical combos
- **Coordinate validation** — warns on screen-edge clicks
- **Rate limiting** — caps at 120 actions/minute

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (no display required)
pytest tests/ -v

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Test Markers

```bash
pytest -m "not integration"   # skip tests that need a real display
pytest -m agent               # only agent/server tests
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `COMPUTER_USE_MODEL` | `openai:gpt-4o` | LLM model string |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `NVIDIA_API_KEY` | — | NVIDIA NIM API key |
| `COMPUTER_USE_PORT` | `8000` | Server port inside container |
| `COMPUTER_USE_HOST` | `0.0.0.0` | Bind address |
| `DISPLAY` | `:99` | X11 display (set automatically in Docker) |
