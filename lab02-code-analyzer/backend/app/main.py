from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .llm import AnalysisClient, create_default_client
from .schemas import AnalyzeRequest, AnalyzeResponse


def create_app(llm_client: AnalysisClient | None = None) -> FastAPI:
    app = FastAPI(title="Lab 02 Code Analyzer API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.llm_client = llm_client or create_default_client()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/analyze", response_model=AnalyzeResponse)
    def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
        try:
            raw = app.state.llm_client.analyze(
                code=payload.code,
                language=payload.language,
                analysis_mode=payload.analysis_mode,
            )
            return AnalyzeResponse.model_validate(raw)
        except ValidationError as exc:
            raise HTTPException(status_code=502, detail="LLM returned invalid structured data") from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


app = create_app()

