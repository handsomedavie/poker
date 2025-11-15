import os
import hmac
import hashlib
import urllib.parse
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from db import get_user, top_balances, set_display_name

APP_DIR = os.path.join(os.path.dirname(__file__), "webapp")
START_BALANCE = 1000

app = FastAPI(title="Poker Mini App Server")

# Serve static assets
app.mount("/webapp", StaticFiles(directory=APP_DIR), name="webapp")


@app.get("/")
async def index():
    index_path = os.path.join(APP_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index not found")
    return FileResponse(index_path)


def _parse_init_data(init_data: str) -> Dict[str, str]:
    # initData is URL-encoded key=value pairs separated by &
    parsed = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
    return {k: v for k, v in parsed}


def _check_telegram_auth(init_data: str, bot_token: str) -> Dict[str, Any]:
    if not init_data:
        raise HTTPException(status_code=401, detail="missing initData")
    data = _parse_init_data(init_data)
    if "hash" not in data:
        raise HTTPException(status_code=401, detail="missing hash")
    tg_hash = data.pop("hash")

    # Build data-check-string in alphabetical order by key
    data_check_arr = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(data_check_arr)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(h, tg_hash):
        raise HTTPException(status_code=401, detail="bad signature")

    # Extract user JSON if present
    user_json = data.get("user")
    user: Dict[str, Any] = {}
    if user_json:
        import json
        try:
            user = json.loads(user_json)
        except Exception:
            user = {}
    return {"data": data, "user": user}


@app.post("/api/me")
async def me(payload: Dict[str, str]):
    init_data = payload.get("initData", "")
    if not init_data:
        # Guest mode for local browser testing
        db_user = await get_user(0, START_BALANCE, "Guest")
        return {
            "user_id": db_user["user_id"],
            "display_name": db_user.get("display_name") or "Guest",
            "balance": db_user["balance"],
        }

    bot_token = os.getenv("TELEGRAM_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="server misconfigured: TELEGRAM_TOKEN not set")
    auth = _check_telegram_auth(init_data, bot_token)
    user = auth.get("user") or {}
    user_id = user.get("id") or 0
    display = user.get("first_name") or "Player"

    db_user = await get_user(user_id, START_BALANCE, display)
    if user_id:
        await set_display_name(user_id, display)
    return {
        "user_id": db_user["user_id"],
        "display_name": db_user.get("display_name") or display,
        "balance": db_user["balance"],
    }


@app.get("/api/top")
async def api_top():
    top = await top_balances(10)
    return {"top": top}
