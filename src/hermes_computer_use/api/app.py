"""FastAPI application for direct tool REST calls.

Each tool is callable via POST /v1/tools/{tool_name} with a JSON body
matching the tool's parameter schema.

Tool implementations are thin wrappers around the same underlying
functions used by the NAT react_agent — no duplication.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from hermes_computer_use.safety.checker import SafetyChecker
from hermes_computer_use.tools.actions import DesktopActionExecutor
from hermes_computer_use.tools.screenshot import capture_screenshot
from hermes_computer_use.tools.window import WindowManager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="hermes-computer-use Tool API",
    description="Direct REST endpoints for Ubuntu desktop automation tools.",
    version="0.2.0",
)

_safety = SafetyChecker()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TakeScreenshotRequest(BaseModel):
    display: str = ":0"
    max_dimension: int = 1024


class MouseMoveRequest(BaseModel):
    x: int
    y: int


class MouseClickRequest(BaseModel):
    x: int
    y: int
    button: str = "left"


class MouseDoubleClickRequest(BaseModel):
    x: int
    y: int


class MouseDragRequest(BaseModel):
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    button: str = "left"


class MouseScrollRequest(BaseModel):
    x: int = 0
    y: int = 0
    direction: str = "down"
    amount: int = 3


class KeyboardTypeRequest(BaseModel):
    text: str


class KeyboardKeyRequest(BaseModel):
    key: str


class KeyboardHotkeyRequest(BaseModel):
    keys: list[str]


class FocusWindowRequest(BaseModel):
    title: str


class CheckSafetyRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/tools")
def list_tools() -> Dict[str, Any]:
    """List all available tool endpoints."""
    return {
        "tools": [
            "take_screenshot",
            "mouse_move",
            "mouse_click",
            "mouse_double_click",
            "mouse_drag",
            "mouse_scroll",
            "keyboard_type",
            "keyboard_key",
            "keyboard_hotkey",
            "list_windows",
            "focus_window",
            "check_action_safety",
        ]
    }


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

@app.post("/v1/tools/take_screenshot")
def tool_take_screenshot(req: TakeScreenshotRequest = TakeScreenshotRequest()) -> Dict[str, Any]:
    """Capture the current screen and return a base64-encoded PNG."""
    os.environ.setdefault("DISPLAY", req.display)
    shot = capture_screenshot()
    if shot is None:
        raise HTTPException(status_code=503, detail="Screenshot capture failed — no display available")
    if req.max_dimension > 0:
        shot = shot.resize(req.max_dimension)
    return {
        "success": True,
        "image_b64": shot.to_base64(),
        "width": shot.width,
        "height": shot.height,
        "urn": shot.to_urn(),
    }


# ---------------------------------------------------------------------------
# Mouse
# ---------------------------------------------------------------------------

@app.post("/v1/tools/mouse_move")
def tool_mouse_move(req: MouseMoveRequest) -> Dict[str, Any]:
    executor = DesktopActionExecutor()
    result = executor.execute("move", x=req.x, y=req.y)
    return {"success": result.success, "x": req.x, "y": req.y, "error": result.error}


@app.post("/v1/tools/mouse_click")
def tool_mouse_click(req: MouseClickRequest) -> Dict[str, Any]:
    check = _safety.check_all("click", x=req.x, y=req.y, button=req.button)
    if not check.safe:
        raise HTTPException(status_code=400, detail=f"Blocked by safety: {check.reason}")
    executor = DesktopActionExecutor()
    result = executor.execute("click", x=req.x, y=req.y, button=req.button)
    return {"success": result.success, "x": req.x, "y": req.y, "button": req.button, "error": result.error}


@app.post("/v1/tools/mouse_double_click")
def tool_mouse_double_click(req: MouseDoubleClickRequest) -> Dict[str, Any]:
    executor = DesktopActionExecutor()
    result = executor.execute("double_click", x=req.x, y=req.y)
    return {"success": result.success, "x": req.x, "y": req.y, "error": result.error}


@app.post("/v1/tools/mouse_drag")
def tool_mouse_drag(req: MouseDragRequest) -> Dict[str, Any]:
    executor = DesktopActionExecutor()
    result = executor.execute("drag", from_x=req.from_x, from_y=req.from_y,
                               to_x=req.to_x, to_y=req.to_y, button=req.button)
    return {"success": result.success, "error": result.error}


@app.post("/v1/tools/mouse_scroll")
def tool_mouse_scroll(req: MouseScrollRequest) -> Dict[str, Any]:
    # Convert direction+amount to delta (positive=down, negative=up).
    delta = req.amount if req.direction in {"down", "right"} else -req.amount
    executor = DesktopActionExecutor()
    result = executor.execute("scroll", x=req.x, y=req.y, delta=delta)
    return {"success": result.success, "direction": req.direction, "amount": req.amount, "error": result.error}


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------

@app.post("/v1/tools/keyboard_type")
def tool_keyboard_type(req: KeyboardTypeRequest) -> Dict[str, Any]:
    check = _safety.check_text(req.text)
    if not check.safe:
        raise HTTPException(status_code=400, detail=f"Blocked by safety: {check.reason}")
    executor = DesktopActionExecutor()
    result = executor.execute("type", text=req.text)
    return {"success": result.success, "error": result.error}


@app.post("/v1/tools/keyboard_key")
def tool_keyboard_key(req: KeyboardKeyRequest) -> Dict[str, Any]:
    executor = DesktopActionExecutor()
    result = executor.execute("key", key=req.key)
    return {"success": result.success, "key": req.key, "error": result.error}


@app.post("/v1/tools/keyboard_hotkey")
def tool_keyboard_hotkey(req: KeyboardHotkeyRequest) -> Dict[str, Any]:
    check = _safety.check_key_combo(req.keys)
    if not check.safe:
        raise HTTPException(status_code=400, detail=f"Blocked by safety: {check.reason}")
    executor = DesktopActionExecutor()
    result = executor.execute("hotkey", keys=req.keys)
    return {"success": result.success, "keys": req.keys, "error": result.error}


# ---------------------------------------------------------------------------
# Window management
# ---------------------------------------------------------------------------

@app.get("/v1/tools/list_windows")
@app.post("/v1/tools/list_windows")
def tool_list_windows() -> Dict[str, Any]:
    mgr = WindowManager()
    windows = mgr.list_windows()
    return {
        "success": True,
        "windows": [
            {
                "window_id": w.window_id,
                "title": w.title,
                "class_name": w.class_name,
                "pid": w.pid,
                "x": w.x,
                "y": w.y,
                "width": w.width,
                "height": w.height,
                "active": w.active,
            }
            for w in windows
        ],
    }


@app.post("/v1/tools/focus_window")
def tool_focus_window(req: FocusWindowRequest) -> Dict[str, Any]:
    mgr = WindowManager()
    windows = mgr.search_windows(req.title)
    if not windows:
        raise HTTPException(status_code=404, detail=f"No window matching '{req.title}'")
    window = windows[0]
    result = mgr.focus_window(window.window_id)
    ok = result.get("success", False) if isinstance(result, dict) else bool(result)
    return {"success": ok, "window_title": window.title, "window_id": window.window_id}


# ---------------------------------------------------------------------------
# Safety check
# ---------------------------------------------------------------------------

@app.post("/v1/tools/check_action_safety")
def tool_check_action_safety(req: CheckSafetyRequest) -> Dict[str, Any]:
    result = _safety.check_all(req.action, **req.params)
    return {
        "safe": result.safe,
        "reason": result.reason,
        "warning": result.warning,
        "blocked": result.blocked,
        "requires_approval": result.requires_approval,
    }
