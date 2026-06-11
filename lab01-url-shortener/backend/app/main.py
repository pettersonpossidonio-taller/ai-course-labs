from __future__ import annotations

import os
import secrets
import string
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from .db import find_by_code, find_by_url, initialize_database, insert_mapping


ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6


class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


def default_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "shortener.db"


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL")


def generate_short_code(length: int = CODE_LENGTH) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="URL Shortener API")
    default_origins = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_origins = [
        origin.strip()
        for origin in os.getenv("FRONTEND_ORIGINS", default_origins).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.db_path = Path(
        db_path or os.getenv("SHORTENER_DB_PATH") or default_db_path()
    )
    initialize_database(app.state.db_path)

    @app.post("/shorten", response_model=ShortenResponse)
    def shorten_url(payload: ShortenRequest, request: Request) -> ShortenResponse:
        validate_url(payload.url)

        existing = find_by_url(request.app.state.db_path, payload.url)
        if existing is not None:
            short_code = existing["short_code"]
            return ShortenResponse(
                short_code=short_code,
                short_url=str(request.url_for("redirect_short_url", short_code=short_code)),
            )

        while True:
            short_code = generate_short_code()
            try:
                insert_mapping(request.app.state.db_path, payload.url, short_code)
                break
            except sqlite3.IntegrityError:
                existing = find_by_url(request.app.state.db_path, payload.url)
                if existing is not None:
                    short_code = existing["short_code"]
                    break

        return ShortenResponse(
            short_code=short_code,
            short_url=str(request.url_for("redirect_short_url", short_code=short_code)),
        )

    @app.get("/{short_code}", name="redirect_short_url")
    def redirect_short_url(short_code: str) -> RedirectResponse:
        mapping = find_by_code(app.state.db_path, short_code)
        if mapping is None:
            raise HTTPException(status_code=404, detail="Short code not found")
        return RedirectResponse(url=mapping["url"], status_code=307)

    return app


app = create_app()
