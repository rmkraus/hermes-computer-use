# hermes-computer-use

Ubuntu desktop automation agent — powered by **NVIDIA NeMo Agent Toolkit**, served as an **OpenAI-compatible API**.

Give it a goal. It sees the screen, reasons about what to do, clicks, types, and navigates — just like a human at a keyboard.

```bash
# Start the agent server
docker compose up

# Send a task via the OpenAI API
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "computer-use",
    "messages": [{"role": "user", "content": "Open Firefox and go to news.ycombinator.com"}]
  }'
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  NVIDIA NeMo Agent Toolkit (nat serve)                   │
│  Serves /v1/chat/completions on port 8000                │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  react_agent (ReAct loop)                        │   │
│  │                                                  │   │
│  │  Goal → screenshot → reason → act → repeat       │   │
│  │                                                  │   │
│  │  Tools:                                          │   │
│  │    take_screenshot    list_windows               │   │
│  │    mouse_click        focus_window               │   │
│  │    mouse_move         keyboard_type              │   │
│  │    mouse_scroll       keyboard_key               │   │
│  │    mouse_double_click keyboard_hotkey            │   │
│  │    check_action_safety                           │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬─────────────────────────────────┘
                         │ /v1/chat/completions
          ┌──────────────┼──────────────┐
          │              │              │
     ┌────┴────┐   ┌─────┴──────┐  ┌───┴──────┐
     │ Hermes  │   │  Any OpenAI │  │  curl /  │
     │ Agent   │   │  client     │  │  scripts │
     └─────────┘   └────────────┘  └──────────┘
```

The agent runs a **ReAct loop** (Reason + Act):
1. Take a screenshot
2. Send it to the LLM with the current goal
3. LLM picks a tool and arguments
4. Execute the tool (with safety checks)
5. Repeat until done

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
# Edit .env and add your NVIDIA_API_KEY
```

### 2. Start

```bash
docker compose up
```

The agent starts a virtual display (Xvfb at 1920×1080) inside the container, launches a window manager, and serves the API on port 8000.

### 3. Send a task

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

response = client.chat.completions.create(
    model="computer-use",
    messages=[
        {"role": "user", "content": "Open the terminal and run: echo 'Hello from the agent'"}
    ]
)
print(response.choices[0].message.content)
```

---

## Integration with Hermes Agent

Add this to your Hermes config to call the agent from Hermes:

```yaml
# ~/.hermes/config.yaml
providers:
  computer_use:
    type: openai_compatible
    base_url: http://localhost:8000/v1
    api_key: not-needed
    model: computer-use
```

Then in Hermes: *"Use computer_use to open Firefox and take a screenshot of the homepage"*

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

- **Blocklist** — blocks dangerous shell commands (`rm -rf`, `mkfs`, `sudo shutdown`), credential input patterns, and system-critical key combos (`ctrl+alt+delete`, `ctrl+alt+esc`)
- **Rate limiting** — prevents runaway loops
- **Coordinate validation** — rejects out-of-bounds clicks
- **Self-check tool** — the agent can call `check_action_safety` before acting when uncertain

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NVIDIA_API_KEY` | — | NVIDIA NIM API key (required unless using OpenAI) |
| `OPENAI_API_KEY` | — | Alternative: use OpenAI as the LLM backend |
| `LLM_MODEL` | `meta/llama-4-scout-17b-16e-instruct` | Vision-capable model to use |
| `LLM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | LLM API base URL |
| `DISPLAY_NUM` | `1` | Xvfb display number |
| `SCREEN_RESOLUTION` | `1920x1080x24` | Virtual display resolution |

### Using a Local vLLM Model

Point the agent at a local vLLM instance serving a vision model:

```bash
LLM_BASE_URL=http://your-vllm-host:8080/v1 \
LLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct \
NVIDIA_API_KEY=not-needed \
docker compose up
```

### Controlling the Host Display

To control the *actual* host desktop instead of the virtual one:

```yaml
# docker-compose.yaml — uncomment these lines:
volumes:
  - /tmp/.X11-unix:/tmp/.X11-unix
environment:
  DISPLAY: ":0"
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

### Run Tests

```bash
uv run python -m pytest tests/ -v
```

### Lint and Type Check

```bash
uv run ruff check src/ tests/
uv run mypy src/
```

### Project Structure

```
hermes-computer-use/
├── src/hermes_computer_use/
│   ├── nat/
│   │   ├── __init__.py
│   │   └── tools.py          # NAT @register_function tool wrappers
│   ├── tools/
│   │   ├── actions.py         # High-level action executor
│   │   ├── input.py           # Mouse + keyboard input simulation
│   │   ├── screenshot.py      # Screen capture (scrot/xwd/pyautogui)
│   │   ├── window.py          # Window management (xdotool)
│   │   └── registry.py        # Tool capability registry
│   └── safety/
│       ├── checker.py         # Action safety checker
│       └── blocklist.py       # Blocked action patterns
├── tests/                     # 158 tests, all passing
├── workflow.yaml              # NAT agent configuration
├── Dockerfile
├── docker-compose.yaml
└── docker-entrypoint.sh
```

---

## License

MIT
