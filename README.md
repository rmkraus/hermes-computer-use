# hermes-computer-use

[![CI](https://github.com/rmkraus/hermes-computer-use/actions/workflows/ci.yml/badge.svg)](https://github.com/rmkraus/hermes-computer-use/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/rmkraus/hermes-computer-use/branch/main/graph/badge.svg)](https://codecov.io/gh/rmkraus/hermes-computer-use)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ubuntu desktop automation agent — a [DeepAgents](https://github.com/langchain-ai/deepagents)
ReAct loop served by [NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) (NAT).

Supports **two serving modes** from the same image:

| Mode | Protocol | Default port | Clients |
|------|----------|-------------|---------|
| `openai` (default) | OpenAI-compatible REST (`/v1/chat/completions`) | 8000 | Hermes, Cursor, `curl`, any OpenAI SDK |
| `mcp` | Model Context Protocol (`/mcp`, streamable-http) | 9901 | Hermes native MCP, Claude Desktop, any MCP client |

The agent takes screenshots, clicks, types, manages windows, and runs shell commands on a real
Ubuntu desktop until the goal is achieved.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     NeMo Agent Toolkit                          │
│  nat serve --config_file workflow.yaml                          │
│                                                                 │
│  POST /v1/chat/completions  ──►  langgraph_wrapper              │
│  (streaming SSE supported)        │                             │
│                                   ▼                             │
│                           DeepAgents ReAct loop                 │
│                           (create_deep_agent)                   │
│                                   │                             │
│                         ┌─────────┴──────────┐                 │
│                         ▼                    ▼                  │
│                   LLM (NIM / any         11 computer-use        │
│                   OpenAI-compat)         tools (below)          │
└─────────────────────────────────────────────────────────────────┘

Tools: take_screenshot · zoom_region · click · move_mouse · scroll
       type_text · key_press · list_windows · focus_window
       run_command · get_screen_info
```

NAT owns all the HTTP serving — streaming, session state, telemetry, eval.
`agent/agent.py` is the thin entrypoint: it calls `SyncBuilder.current().get_llm()`
to get the NAT-configured LLM, then hands it to `create_deep_agent()` with the tool list.

---

## Quickstart

### Docker (recommended)

```bash
cp .env.example .env
# Set NVIDIA_API_KEY in .env
```

**OpenAI mode** (default) — `POST /v1/chat/completions` on port 8002:
```bash
docker run --rm -p 8002:8000 --env-file .env hermes-computer-use:latest
# or with docker compose:
docker compose up computer-use-openai
```

**MCP mode** — streamable-http `/mcp` on port 9901:
```bash
docker run --rm -p 9901:9901 --env-file .env hermes-computer-use:latest mcp
# or with docker compose:
docker compose up computer-use-mcp
```

**Override the LLM at runtime** — model, base URL, and API key can all be set via
environment variables or `--override` flags. Both approaches work with either mode:

```bash
# Via environment variables (simplest)
docker run --rm -p 8002:8000 \
    -e NVIDIA_API_KEY=nvapi-... \
    -e COMPUTER_USE_MODEL=meta/llama-4-scout-17b-16e-instruct \
    -e NIM_BASE_URL=https://integrate.api.nvidia.com/v1 \
    hermes-computer-use:latest

# Point at a local vLLM instance instead of NVIDIA NIM
docker run --rm -p 8002:8000 \
    -e NIM_BASE_URL=http://host.docker.internal:8000/v1 \
    -e NVIDIA_API_KEY=unused \
    -e COMPUTER_USE_MODEL=my-local-model \
    hermes-computer-use:latest

# Via NAT --override flags (passed through after the mode selector)
docker run --rm -p 8002:8000 --env-file .env hermes-computer-use:latest openai \
    --override llms.agent.model meta/llama-4-scout-17b-16e-instruct \
    --override llms.agent.base_url https://integrate.api.nvidia.com/v1 \
    --override llms.agent.api_key nvapi-...

# MCP mode with overrides
docker run --rm -p 9901:9901 --env-file .env hermes-computer-use:latest mcp \
    --override llms.agent.model gpt-4o \
    --override llms.agent.base_url https://api.openai.com/v1 \
    --override llms.agent.api_key sk-...
```

Any extra arguments after `openai` or `mcp` are passed through directly to `nat`.

### Bare metal

```bash
# Install with NAT serving layer
pip install -e ".[all]"

# Set your API key
export NVIDIA_API_KEY=nvapi-...

# Start the server
nat serve --config_file workflow.yaml
```

---

## Configuration

Model, endpoint, and API key are set via environment variables or NAT `--override` flags.
The `workflow.yaml` reads them at startup:

```yaml
llms:
  agent:
    _type: nim
    model: ${COMPUTER_USE_MODEL:-meta/llama-3.2-11b-vision-instruct}
    api_key: ${NVIDIA_API_KEY}
    base_url: ${NIM_BASE_URL:-null}   # null = NVIDIA NIM; set for local vLLM / custom endpoint
```

### Environment variables (recommended)

```bash
# NVIDIA NIM (default)
export NVIDIA_API_KEY=nvapi-...
export COMPUTER_USE_MODEL=meta/llama-3.2-11b-vision-instruct
export NIM_BASE_URL=https://integrate.api.nvidia.com/v1   # optional, NIM default

# Local vLLM
export NIM_BASE_URL=http://localhost:8000/v1
export NVIDIA_API_KEY=unused
export COMPUTER_USE_MODEL=my-local-model

# OpenAI
export NIM_BASE_URL=https://api.openai.com/v1
export NVIDIA_API_KEY=sk-...
export COMPUTER_USE_MODEL=gpt-4o
```

### NAT `--override` flags

```bash
nat serve --config_file workflow.yaml \
    --override llms.agent.model meta/llama-4-scout-17b-16e-instruct \
    --override llms.agent.base_url https://integrate.api.nvidia.com/v1 \
    --override llms.agent.api_key nvapi-...
```

---

## API Usage

NAT exposes a fully streaming OpenAI-compatible endpoint.

### Non-streaming

```bash
curl http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hermes-computer-use",
    "messages": [{"role": "user", "content": "Open a terminal and print the current date"}]
  }'
```

### Streaming (SSE)

```bash
curl http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hermes-computer-use",
    "stream": true,
    "messages": [{"role": "user", "content": "Take a screenshot and describe what you see"}]
  }'
```

### Python (OpenAI client)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8002/v1", api_key="unused")

stream = client.chat.completions.create(
    model="hermes-computer-use",
    messages=[{"role": "user", "content": "Open Firefox and navigate to example.com"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

---

## Hermes Agent Integration

Use the **MCP mode** so the computer-use tools appear natively alongside Hermes's
built-in tools — no secondary provider or manual model switching needed.

### 1. Start the container in MCP mode

```bash
docker run -d --rm -p 9901:9901 --env-file .env hermes-computer-use:latest mcp
```

### 2. Add to `~/.hermes/config.yaml`

```yaml
mcp_servers:
  computer_use:
    url: http://localhost:9901/mcp
    timeout: 120        # agent tasks can take a while
    connect_timeout: 30
```

Restart Hermes. The computer-use tools are auto-discovered and registered as
`mcp_computer_use_*` — available in every conversation without any extra commands.

### 3. Use it

Just ask naturally — Hermes picks the right tool:

```
Take a screenshot of the desktop
Open a terminal and check disk usage
Click on the Firefox icon and navigate to example.com
```

### OpenAI mode (alternative)

If you prefer to route tasks to it as a separate model/provider rather than
having the tools always available, use the OpenAI frontend instead:

```yaml
# ~/.hermes/config.yaml
providers:
  computer_use:
    type: openai
    base_url: http://localhost:8002/v1
    api_key: unused
    model: hermes-computer-use
```

Then explicitly ask Hermes to use that provider for a task.

---

## Tool Catalog

| Tool | Description |
|---|---|
| `take_screenshot` | Capture full desktop; optional `max_dimension` resize |
| `zoom_region` | Crop and magnify a screen region for reading small text |
| `click` | Left/right/double-click at (x, y) |
| `move_mouse` | Move cursor to (x, y) with configurable duration |
| `scroll` | Scroll at (x, y) by N clicks up/down |
| `type_text` | Type text via keyboard |
| `key_press` | Press keys or hotkeys: `enter`, `ctrl+c`, `ctrl+alt+t` |
| `list_windows` | List all open windows with IDs, titles, geometry |
| `focus_window` | Bring a window to the foreground by ID |
| `run_command` | Run a shell command (timeout enforced) |
| `get_screen_info` | Return display server type, resolution, and DISPLAY var |

---

## Development

```bash
# Install dev dependencies
pip install -e ".[all,dev]"    # Note: nvidia-nat requires separate install
uv pip install nvidia-nat[langchain]

# Run tests (no display or LLM credentials needed)
pytest tests/ -q

# Lint
ruff check src/ tests/
```

Tests mock NAT, deepagents, pyautogui, and all display calls — the full suite
runs in CI without any GPU, display server, or API keys.

---

## Requirements

- **OS**: Ubuntu 22.04+ (Wayland not supported; X11 required)
- **Python**: 3.11+
- **Display**: X11 display (real or Xvfb)
- **LLM**: Any NIM-compatible vision model (`NVIDIA_API_KEY`) or local vLLM (`NIM_BASE_URL`)
- **System tools**: `xdotool` for window management

---

## License

MIT — see [LICENSE](LICENSE).
