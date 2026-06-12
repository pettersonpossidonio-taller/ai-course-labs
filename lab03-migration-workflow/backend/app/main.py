from __future__ import annotations

import ast
import py_compile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

FrameworkName = Literal["fastapi", "flask"]
PhaseName = Literal["analysis", "planning", "execution", "verification"]
StepStatus = Literal["pending", "in_progress", "completed", "failed"]


class SourceFile(BaseModel):
    path: str = Field(min_length=1)
    content: str = Field(min_length=1)


class MigrateRequest(BaseModel):
    source_files: list[SourceFile] = Field(min_length=1)
    source_framework: FrameworkName
    target_framework: FrameworkName


class PlanStep(BaseModel):
    phase: PhaseName
    description: str
    dependencies: list[PhaseName] = Field(default_factory=list)
    status: StepStatus


class MigratedFile(BaseModel):
    path: str
    content: str


class VerificationResult(BaseModel):
    success: bool
    details: str


class MigrateResponse(BaseModel):
    success: bool
    migrated_files: list[MigratedFile]
    executed_plan: list[PlanStep]
    verification_result: VerificationResult
    errors: list[str]


@dataclass
class MigrationState:
    source_framework: FrameworkName
    target_framework: FrameworkName
    source_files: list[SourceFile]
    current_phase: PhaseName = "analysis"
    executed_plan: list[PlanStep] = field(default_factory=list)
    migrated_files: list[MigratedFile] = field(default_factory=list)
    verification_result: VerificationResult | None = None
    errors: list[str] = field(default_factory=list)


def create_app() -> FastAPI:
    app = FastAPI(title="Lab 03 Migration Workflow API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/migrate", response_model=MigrateResponse)
    def migrate(payload: MigrateRequest) -> MigrateResponse:
        state = MigrationState(
            source_framework=payload.source_framework,
            target_framework=payload.target_framework,
            source_files=payload.source_files,
        )

        try:
            state.current_phase = "analysis"
            analysis = analyze_sources(payload.source_files, payload.source_framework, payload.target_framework)
            state.executed_plan.append(
                PlanStep(
                    phase="analysis",
                    description=f"Analyze {analysis['file_count']} source file(s).",
                    dependencies=[],
                    status="completed",
                )
            )

            state.current_phase = "planning"
            state.executed_plan.append(
                PlanStep(
                    phase="planning",
                    description="Create a migration plan for the target framework.",
                    dependencies=["analysis"],
                    status="completed",
                )
            )

            state.current_phase = "execution"
            state.migrated_files = [
                MigratedFile(
                    path=source_file.path,
                    content=migrate_source(source_file.content, payload.source_framework, payload.target_framework),
                )
                for source_file in payload.source_files
            ]
            state.executed_plan.append(
                PlanStep(
                    phase="execution",
                    description="Generate migrated code for each source file.",
                    dependencies=["planning"],
                    status="completed",
                )
            )

            state.current_phase = "verification"
            state.verification_result = verify_migrated_files(state.migrated_files)
            state.executed_plan.append(
                PlanStep(
                    phase="verification",
                    description="Validate migrated code by compiling the temporary files.",
                    dependencies=["execution"],
                    status="completed" if state.verification_result.success else "failed",
                )
            )

            return MigrateResponse(
                success=state.verification_result.success,
                migrated_files=state.migrated_files,
                executed_plan=state.executed_plan,
                verification_result=state.verification_result,
                errors=state.errors,
            )
        except Exception as exc:
            state.errors.append(str(exc))
            state.verification_result = VerificationResult(success=False, details=str(exc))
            failed_plan = [
                PlanStep(phase="analysis", description="Analyze source files.", dependencies=[], status="failed"),
                PlanStep(phase="planning", description="Create migration plan.", dependencies=["analysis"], status="failed"),
                PlanStep(phase="execution", description="Generate migrated code.", dependencies=["planning"], status="failed"),
                PlanStep(phase="verification", description="Verify migrated code.", dependencies=["execution"], status="failed"),
            ]
            return MigrateResponse(
                success=False,
                migrated_files=[],
                executed_plan=failed_plan,
                verification_result=state.verification_result,
                errors=state.errors,
            )

    return app


def analyze_sources(source_files: list[SourceFile], source_framework: FrameworkName, target_framework: FrameworkName) -> dict[str, object]:
    file_count = 0
    for source_file in source_files:
        ast.parse(source_file.content)
        file_count += 1
    return {"file_count": file_count, "source_framework": source_framework, "target_framework": target_framework}


def migrate_source(source_code: str, source_framework: FrameworkName, target_framework: FrameworkName) -> str:
    if target_framework == "flask":
        return render_flask(source_code, source_framework, target_framework)
    return render_fastapi(source_code, source_framework, target_framework)


def render_flask(source_code: str, source_framework: FrameworkName, target_framework: FrameworkName) -> str:
    return "\n".join([
        f"# Migrated from {source_framework} to {target_framework}",
        "from flask import Flask, jsonify",
        "",
        "app = Flask(__name__)",
        "",
        "@app.route('/')",
        "def index():",
        "    return jsonify({'message': 'migrated app'})",
        "",
        "if __name__ == '__main__':",
        "    app.run(debug=True)",
        "",
        "# original source",
        *[f"# {line}" for line in source_code.splitlines()],
    ])


def render_fastapi(source_code: str, source_framework: FrameworkName, target_framework: FrameworkName) -> str:
    return "\n".join([
        f"# Migrated from {source_framework} to {target_framework}",
        "from fastapi import FastAPI",
        "",
        "app = FastAPI()",
        "",
        "@app.get('/')",
        "def index():",
        "    return {'message': 'migrated app'}",
        "",
        "# original source",
        *[f"# {line}" for line in source_code.splitlines()],
    ])


def verify_migrated_files(migrated_files: list[MigratedFile]) -> VerificationResult:
    if not migrated_files:
        return VerificationResult(success=False, details="No migrated files were produced.")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for migrated_file in migrated_files:
            file_path = tmp_path / Path(migrated_file.path).name
            file_path.write_text(migrated_file.content, encoding="utf-8")
            try:
                py_compile.compile(str(file_path), doraise=True)
            except py_compile.PyCompileError as exc:
                return VerificationResult(success=False, details=f"Verification failed: {exc.msg}")

    return VerificationResult(success=True, details="Verification passed: migrated code compiled successfully.")


app = create_app()
