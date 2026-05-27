# hermes-computer-use

Ubuntu desktop automation agent served as an OpenAI-compatible API.

Point any OpenAI client at it and it will control a real Ubuntu desktop — taking
screenshots, moving the mouse, typing, pressing keys, managing windows, and
running shell commands.

## Architecture

```
Your client (Hermes, Cursor, curl, ...)
        │  POST /v1/chat/completions
        ▼
  NAT FastAPI server  (workflow.yaml)
        │  react_agent loop
        ▼
  @register_function tools
   ├── take_screenshot / zoom_region
   ├── click / move_mouse / scroll
   ├── type_text / key_press
   ├── run_command
   ├── list_windows / focus_window
   └── get_screen_info
        │
        ▼
  Xvfb virtual display  (or real X11)
```

Tools are registered with NAT via the `nat.plugins` entry point in
`pyproject.toml`. The `react_agent` loop handles multi-turn reasoning,
tool selection, and error recovery.

## Quickstart

### Docker (recommended)

```bash
cp .env.example .env
# edit .env — set NVIDIA_API_KEY at minimum
docker compose up
```

The OpenAI-compatible API is available at `http://localhost:8002/v1/chat/completions`.

### Bare metal

```bash
# Install with uv
uv pip install -e .

# Start Xvfb (or use your existing display)
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Set env vars
export NVIDIA_API_KEY=nvapi-...
export COMPUTER_USE_MODEL=meta/llama-3.2-11b-vision-instruct  # optional

# Serve
nat serve --config_file workflow.yaml
```

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|---|---|---|
| `NVIDIA_API_KEY` | *(required)* | NIM API key from [build.nvidia.com](https://build.nvidia.com) |
| `COMPUTER_USE_MODEL` | `meta/llama-3.2-11b-vision-instruct` | Vision+tool-calling model |
| `NIM_BASE_URL` | *(api.nvidia.com)* | Override NIM endpoint (e.g. local vLLM) |
| `COMPUTER_USE_PORT` | `8000` | Port inside the container |

To use a local vLLM instance instead of NVIDIA's cloud:

```bash
NIM_BASE_URL=http://localhost:8000/v1 \
COMPUTER_USE_MODEL=your-local-model \
nat serve --config_file workflow.yaml
```

Override any workflow setting at runtime:

```bash
nat serve --config_file workflow.yaml \
  --override llms.agent.model meta/llama-4-scout-17b-16e-instruct
```

## Calling the API

```bash
curl http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "computer-use",
    "messages": [{"role": "user", "content": "Take a screenshot and tell me what is on the desktop."}]
  }'
```

## Hermes integration

Add to your Hermes config (`~/.hermes/config.yaml`):

```yaml
models:
  computer_use:
    provider: openai
    model: computer-use
    base_url: http://localhost:8002/v1
    api_key: unused
```

Then in Hermes: *"Using the computer_use model, open Firefox and go to example.com"*

## systemd (production)

```bash
sudo cp scripts/hermes-computer-use.service /etc/systemd/system/
sudo cp scripts/hermes-computer-use.env.example /etc/hermes-computer-use.env
# edit /etc/hermes-computer-use.env — set NVIDIA_API_KEY
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-computer-use
journalctl -u hermes-computer-use -f
```

## Available tools

| Tool | Description |
|---|---|
| `take_screenshot` | Full-screen screenshot → base64 PNG data URI |
| `zoom_region` | Crop and zoom a screen region (for reading small text) |
| `click` | Click at (x, y) — left/right/middle, single/double |
| `move_mouse` | Move cursor without clicking |
| `type_text` | Type a string via keyboard |
| `key_press` | Press a key or hotkey (`ctrl+c`, `alt+F4`, etc.) |
| `scroll` | Scroll up/down at a position |
| `run_command` | Run a shell command, returns stdout/stderr |
| `list_windows` | List visible windows (JSON) |
| `focus_window` | Raise and focus a window by title substring |
| `get_screen_info` | Display info: server type, resolution, DISPLAY var |

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src/ tests/
```

## License

MIT
