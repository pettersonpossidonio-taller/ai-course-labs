from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .llm import AnalysisClient, RuleBasedAnalysisClient, create_default_client
from .schemas import AnalyzeRequest, AnalyzeResponse


logger = logging.getLogger(__name__)


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
        except Exception:
            logger.warning("LLM unavailable, using fallback analyzer", exc_info=True)
            fallback_client = RuleBasedAnalysisClient()
            fallback_raw = fallback_client.analyze(
                code=payload.code,
                language=payload.language,
                analysis_mode=payload.analysis_mode,
            )
            return AnalyzeResponse.model_validate(fallback_raw)

    return app


app = create_app()
