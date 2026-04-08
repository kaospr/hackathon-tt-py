"""
Ghostfolio pytx — FastAPI entry point.

Mirrors main.ts + app.module.ts: bootstraps the app and wires modules.
All portfolio logic lives under app/implementation/, with HTTP wiring
in app/wrapper/. This file is part of the immutable wrapper layer.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .wrapper.portfolio.portfolio_controller import create_portfolio_router

app = FastAPI(title="Ghostfolio pytx")

# ---------------------------------------------------------------------------
# In-memory store (mirrors Prisma user/account persistence)
# ---------------------------------------------------------------------------

@dataclass
class UserState:
    access_token: str
    auth_token: str
    base_currency: str = "USD"
    activities: list[dict] = field(default_factory=list)
    market_data: dict[str, dict[str, list[dict]]] = field(default_factory=dict)


_lock = threading.Lock()
_users: dict[str, UserState] = {}
_access_to_auth: dict[str, str] = {}


def _make_tokens() -> tuple[str, str]:
    return str(uuid.uuid4()), str(uuid.uuid4())


def _get_user(authorization: str | None = Header(default=None)) -> UserState:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    with _lock:
        user = _users.get(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token")
    return user


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# User lifecycle (mirrors user.controller.ts)
# ---------------------------------------------------------------------------

@app.post("/api/v1/user")
def create_user() -> dict:
    access_token, auth_token = _make_tokens()
    user = UserState(access_token=access_token, auth_token=auth_token)
    with _lock:
        _users[auth_token] = user
        _access_to_auth[access_token] = auth_token
    return {"accessToken": access_token, "authToken": auth_token}


@app.put("/api/v1/user/setting")
def update_user_setting(body: dict[str, Any], user: UserState = Depends(_get_user)) -> dict:
    if "baseCurrency" in body:
        user.base_currency = body["baseCurrency"]
    return {"baseCurrency": user.base_currency}


@app.delete("/api/v1/user")
def delete_user(body: dict[str, Any], user: UserState = Depends(_get_user)) -> JSONResponse:
    with _lock:
        auth = _access_to_auth.pop(body.get("accessToken", ""), None)
        if auth:
            _users.pop(auth, None)
    return JSONResponse(status_code=status.HTTP_200_OK, content={})


# ---------------------------------------------------------------------------
# Activities (mirrors activities.controller.ts)
# ---------------------------------------------------------------------------

@app.post("/api/v1/import")
async def import_activities(request: Request, user: UserState = Depends(_get_user)) -> dict:
    body = await request.json()
    activities = body.get("activities", [])
    user.activities.extend(activities)
    return {"activities": activities}


# ---------------------------------------------------------------------------
# Market data seeding (mirrors market-data endpoints)
# ---------------------------------------------------------------------------

@app.post("/api/v1/market-data/{data_source}/{symbol}")
async def seed_market_data(
    data_source: str, symbol: str, request: Request, user: UserState = Depends(_get_user),
) -> dict:
    body = await request.json()
    user.market_data.setdefault(data_source, {})[symbol] = body.get("marketData", [])
    return {}


# ---------------------------------------------------------------------------
# Portfolio module (mirrors portfolio.module.ts)
# ---------------------------------------------------------------------------

app.include_router(create_portfolio_router(_get_user))
