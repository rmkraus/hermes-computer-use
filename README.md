# hermes-computer-use

Ubuntu desktop automation agent — powered by **NVIDIA NeMo Agent Toolkit (NAT)**, served as an **OpenAI-compatible API**.

Give it a goal in plain English. It sees the screen, reasons about what to do, clicks, types, and navigates — autonomously, in a loop — until the task is done.

```bash
# Start the agent
docker compose up -d

# Give it a task
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "computer-use",
    "messages": [{"role": "user", "content": "Open Firefox and go to news.ycombinator.com"}]
  }'
```

---

## Architecture

Everything flows through a single port and a single API — the NAT `react_agent` on port 8000.

```
┌──────────────────────────────────────────────────────────┐
│  NVIDIA NeMo Agent Toolkit  (nat serve)                  │
│  POST /v1/chat/completions  →  port 8000                 │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  react_agent  (ReAct loop)                       │   │
│  │                                                  │   │
│  │  goal → screenshot → reason → act → repeat       │   │
│  │                                                  │   │
│  │  Tools:                                          │   │
│  │    take_screenshot      list_windows             │   │
│  │    mouse_click          focus_window             │   │
│  │    mouse_move           keyboard_type            │   │
│  │    mouse_scroll         keyboard_key             │   │
│  │    mouse_double_click   keyboard_hotkey          │   │
│  │    check_action_safety                           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Ubuntu desktop  (real X display or Xvfb)        │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────┘
                           │  /v1/chat/completions
             ┌─────────────┼─────────────┐
             │             │             │
        ┌────┴────┐  ┌─────┴──────┐  ┌──┴───────┐
        │ Hermes  │  │ Any OpenAI │  │  curl /  │
        │ Agent   │  │   client   │  │  scripts │
        └─────────┘  └────────────┘  └──────────┘
```

### How Hermes uses it

Hermes calls `computer_use(action="run_goal", goal="...")` — one tool call with a
natural-language goal. The NAT react_agent runs the full loop autonomously and
returns a text summary when done. **Hermes never sees individual clicks or
screenshots** — it sends a goal, gets back a result.

```
Hermes main model
  → computer_use(action="run_goal", goal="Open Firefox and go to google.com")
    → POST http://localhost:8000/v1/chat/completions
      → NAT react_agent loop (inside container):
          take_screenshot → reason → mouse_click(Firefox icon)
          take_screenshot → reason → keyboard_type("google.com") → keyboard_key("Return")
          take_screenshot → ✓ goal achieved
      → returns "Successfully opened Firefox and navigated to google.com"
  ← Hermes sees that summary string
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- An NVIDIA API key from [build.nvidia.com](https://build.nvidia.com) (free tier available)

### 1. Clone and configure

```bash
git clone https://github.com/rmkraus/hermes-computer-use
cd hermes-computer-use
cp .env.example .env
# Edit .env — add your NVIDIA_API_KEY
```

### 2. Start

```bash
docker compose up -d
```

This starts a container with an internal **Xvfb virtual display** (1920×1080) and
launches the NAT server on port 8000. The agent has a fresh, isolated desktop to
work on.

### 3. Send a task

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

response = client.chat.completions.create(
    model="computer-use",
    messages=[{"role": "user", "content": "Open the terminal and run: echo 'Hello'"}]
)
print(response.choices[0].message.content)
```

---

## Display Modes

### Default: Xvfb virtual display (isolated)

The container starts its own virtual X display. Nothing on the host desktop is
touched. Best for automation, CI, and headless servers.

```bash
docker compose up -d
```

### Host display: control the real desktop

To have the agent control your actual running desktop, use the host-display
override. This mounts the host X socket and Xauthority file into the container.

**One-time host setup** (re-run after logout):
```bash
xhost +local:docker
```

**Start with host display:**
```bash
docker compose -f docker-compose.yaml -f docker-compose.host-display.yaml up -d
```

`DISPLAY` and `XAUTHORITY` are forwarded from your shell environment
automatically. If `DISPLAY` is unset it defaults to `:0`. If `XAUTHORITY` is
unset it defaults to `~/.Xauthority`.

#### What the override does

`docker-compose.host-display.yaml` mounts the host Xauthority to a **fixed
container path** (`/tmp/.host-Xauthority`) regardless of where it lives on the
host (`/root/.Xauthority`, `/run/user/1000/gdm/Xauthority`, etc.):

```yaml
volumes:
  - /tmp/.X11-unix:/tmp/.X11-unix:rw
  - "${XAUTHORITY:-${HOME}/.Xauthority}:/tmp/.host-Xauthority:ro"
environment:
  DISPLAY: "${DISPLAY:-:0}"
  XAUTHORITY: "/tmp/.host-Xauthority"
```

The entrypoint exports `XAUTHORITY` before probing the display, so
authentication is established before any X connection is attempted.

#### Xvfb fallback

If `DISPLAY` is set but the X server isn't reachable (e.g. you passed `:0` but
the host display isn't mounted), the entrypoint falls back to starting Xvfb on
that display number. The host Xauthority is **unset** in this case to avoid
auth failures with the fresh Xvfb server.

### Bare metal (no Docker)

If the machine already has an X display you can run the NAT server directly:

```bash
git clone https://github.com/rmkraus/hermes-computer-use
cd hermes-computer-use
uv venv --python 3.11 && uv pip install -e .
DISPLAY=:0 NVIDIA_API_KEY=your-key nat serve --config_file workflow.yaml
```

---

## Integration with Hermes Agent

On Linux, Hermes auto-selects the NAT backend when the server is reachable.
No config changes needed — just start the container and enable the tool:

```bash
docker compose up -d
hermes tools enable computer_use
```

Then ask Hermes to do something on the desktop:

> *"Use computer_use to open Firefox, go to github.com/rmkraus, and take a screenshot of the page."*

Hermes calls `computer_use(action="run_goal", goal="...")` which delegates
the entire task to the NAT subagent. The subagent runs the full loop and
returns a summary.

---

## Tools

| Tool | Description |
|------|-------------|
| `take_screenshot` | Capture current screen as base64 PNG |
| `mouse_move` | Move cursor to (x, y) |
| `mouse_click` | Click at (x, y) with optional button |
| `mouse_double_click` | Double-click at (x, y) |
| `mouse_scroll` | Scroll at (x, y) by delta |
| `keyboard_type` | Type a string of text |
| `keyboard_key` | Press a single key (Return, Tab, Escape, etc.) |
| `keyboard_hotkey` | Press a key combo (ctrl+c, alt+F4, etc.) |
| `list_windows` | List open windows with title, size, PID |
| `focus_window` | Focus a window by title substring |
| `check_action_safety` | Validate an action against the safety blocklist |

---

## Safety

All actions pass through a **safety checker** before execution:

- **Blocklist** — blocks dangerous shell commands (`rm -rf`, `mkfs`, `sudo shutdown`), credential-harvesting patterns, and system-critical key combos (`ctrl+alt+delete`, `ctrl+alt+esc`)
- **Coordinate validation** — rejects out-of-bounds clicks
- **Rate limiting** — prevents runaway action loops
- **Self-check tool** — the agent can call `check_action_safety` before acting when uncertain

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NVIDIA_API_KEY` | — | NVIDIA NIM API key (required unless using OpenAI) |
| `OPENAI_API_KEY` | — | Alternative: use OpenAI as the LLM backend |
| `LLM_MODEL` | `meta/llama-4-scout-17b-16e-instruct` | Vision-capable model name |
| `LLM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | LLM API base URL |
| `DISPLAY` | `:1` (Xvfb) | X display to control; set to `:0` for host display |
| `DISPLAY_NUM` | `1` | Xvfb display number (ignored if `DISPLAY` is accessible) |
| `SCREEN_RESOLUTION` | `1920x1080x24` | Virtual display resolution (Xvfb only) |

### Using a local vLLM instance

```bash
LLM_BASE_URL=http://your-vllm-host:8080/v1 \
LLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct \
NVIDIA_API_KEY=placeholder \
docker compose up -d
```

---

## Development

### Install

```bash
git clone https://github.com/rmkraus/hermes-computer-use
cd hermes-computer-use
uv venv --python 3.11
uv pip install -e ".[dev]"
```

### Run tests

```bash
uv run python -m pytest tests/ -v
```

### Lint and type check

```bash
uv run ruff check src/ tests/
uv run mypy src/
```

### Project structure

```
hermes-computer-use/
├── src/hermes_computer_use/
│   ├── nat/
│   │   ├── __init__.py
│   │   └── tools.py          # NAT @register_function tool wrappers
│   ├── tools/
│   │   ├── actions.py         # High-level action executor
│   │   ├── input.py           # Mouse + keyboard input (pyautogui)
│   │   ├── screenshot.py      # Screen capture (scrot / xdotool / pyautogui)
│   │   ├── window.py          # Window management (xdotool)
│   │   └── registry.py        # Tool capability registry
│   └── safety/
│       ├── checker.py         # Action safety checker
│       └── blocklist.py       # Blocked action patterns
├── tests/                     # 170+ tests, all passing
├── workflow.yaml              # NAT react_agent configuration
├── Dockerfile
├── docker-compose.yaml                # Default: Xvfb virtual display
├── docker-compose.host-display.yaml   # Override: use host X display
└── docker-entrypoint.sh
```

---

## License

MIT
