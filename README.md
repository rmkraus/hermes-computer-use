# hermes-computer-use

[![CI](https://github.com/rmkraus/hermes-computer-use/actions/workflows/ci.yml/badge.svg)](https://github.com/rmkraus/hermes-computer-use/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/rmkraus/hermes-computer-use/branch/main/graph/badge.svg)](https://codecov.io/gh/rmkraus/hermes-computer-use)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ubuntu desktop automation agent — a [DeepAgents](https://github.com/langchain-ai/deepagents)
ReAct loop served by [NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) (NAT)
with a streaming OpenAI-compatible `/v1/chat/completions` endpoint.

Any OpenAI client (Hermes Agent, Cursor, Claude Desktop, `curl`) can drive the agent by sending
a plain-English goal. The agent takes screenshots, clicks, types, manages windows, and runs
shell commands on a real Ubuntu desktop until the goal is achieved.

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
docker compose up
```

The server starts on **`http://localhost:8002`** (host port 8002 → container 8000).

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

Model and endpoint are set via `workflow.yaml` (env vars override at runtime):

```yaml
llms:
  agent:
    _type: nim
    model: ${COMPUTER_USE_MODEL:-meta/llama-3.2-11b-vision-instruct}
    api_key: ${NVIDIA_API_KEY}
    base_url: ${NIM_BASE_URL:-null}   # override for local vLLM / custom NIM
```

Override the model at launch without editing the YAML:

```bash
# Use a different NIM model
COMPUTER_USE_MODEL=meta/llama-3.3-70b-instruct nat serve --config_file workflow.yaml

# Point at a local vLLM endpoint
NIM_BASE_URL=http://localhost:8000/v1 nat serve --config_file workflow.yaml

# Or via NAT --override flag
nat serve --config_file workflow.yaml \
  --override llms.agent.model meta/llama-3.3-70b-instruct
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

Add hermes-computer-use as a secondary model in your Hermes config:

```yaml
# ~/.hermes/config.yaml
providers:
  computer_use:
    type: openai
    base_url: http://localhost:8002/v1
    api_key: unused
    model: hermes-computer-use
```

Then in a Hermes session:

```
Use the computer_use provider to open a terminal and check disk usage
```

---

## Tool Catalog

| Tool | Description |
|---|---|
| `take_screenshot` | Capture full desktop; optional `max_dimension` resize |
| `zoom_region` | Crop and magnify a screen region for reading small text |
| `click` | Left/right/double-click at (x, y) |
| `move_mouse` | Move cursor to (x, y) with configurable duration |
| `scroll` | Scroll at (x, y) by N clicks up/down |
| `type_text` | Type text via keyboard (safety-checked) |
| `key_press` | Press keys or hotkeys: `enter`, `ctrl+c`, `ctrl+alt+t` |
| `list_windows` | List all open windows with IDs, titles, geometry |
| `focus_window` | Bring a window to the foreground by ID |
| `run_command` | Run a shell command (safety-checked, timeout enforced) |
| `get_screen_info` | Return display server type, resolution, and DISPLAY var |

---

## Safety

All destructive actions pass through `SafetyChecker` before execution:

- **Coordinate bounds** — clicks/moves stay within screen dimensions
- **Blocklisted commands** — `rm -rf`, `mkfs`, `dd if=`, etc. are rejected
- **Dangerous key combos** — `ctrl+alt+delete`, `alt+f4`, etc. are blocked
- **Sensitive text** — patterns matching passwords/secrets are rejected
- **Rate limiting** — max 60 actions per 60-second window

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
