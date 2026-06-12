from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

AgentName = Literal["Supervisor", "Researcher", "Writer"]


class RunRequest(BaseModel):
    task: str = Field(min_length=1)
    max_iterations: int = Field(default=5, ge=1, le=10)


class ActivityEntry(BaseModel):
    step: int
    agent: AgentName
    content: str


class AgentOutput(BaseModel):
    agent: AgentName
    output: str


class RunResponse(BaseModel):
    final_result: str
    activity_history: list[ActivityEntry]
    agent_outputs: list[AgentOutput]
    iterations_used: int
    forced_completion: bool


@dataclass
class WorkflowState:
    iterations_used: int = 0
    activity_history: list[ActivityEntry] = field(default_factory=list)
    agent_outputs: list[AgentOutput] = field(default_factory=list)


def create_app() -> FastAPI:
    app = FastAPI(title="Lab 05 Multi-Agent API")
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

    @app.post("/run", response_model=RunResponse)
    def run_workflow(payload: RunRequest) -> RunResponse:
        state = WorkflowState()

        delegate_task = supervisor_delegate(payload.task)
        if not add_step(
            state,
            "Supervisor",
            delegate_task,
            payload.max_iterations,
            step_kind="delegate",
        ):
            return finish_with_forced_completion(state, payload.task)

        researcher_output = researcher_step(payload.task, delegate_task)
        if not add_step(state, "Researcher", researcher_output, payload.max_iterations):
            return finish_with_forced_completion(state, payload.task)

        writer_output = writer_step(payload.task, researcher_output)
        if not add_step(state, "Writer", writer_output, payload.max_iterations):
            return finish_with_forced_completion(state, payload.task)

        final_text = supervisor_finalize(payload.task, researcher_output, writer_output)
        final_content = format_final(final_text)
        if not add_step(state, "Supervisor", final_content, payload.max_iterations):
            return finish_with_forced_completion(state, payload.task, researcher_output, writer_output)

        return RunResponse(
            final_result=final_content,
            activity_history=state.activity_history,
            agent_outputs=state.agent_outputs,
            iterations_used=state.iterations_used,
            forced_completion=False,
        )

    return app


app = create_app()


def add_step(
    state: WorkflowState,
    agent: AgentName,
    content: str,
    max_iterations: int,
    *,
    step_kind: str = "output",
) -> bool:
    if state.iterations_used >= max_iterations:
        return False

    state.iterations_used += 1
    state.activity_history.append(
        ActivityEntry(
            step=state.iterations_used,
            agent=agent,
            content=content,
        )
    )
    state.agent_outputs.append(AgentOutput(agent=agent, output=content))
    logger.info("%s step completed: %s", step_kind, agent)
    return True


def finish_with_forced_completion(
    state: WorkflowState,
    task: str,
    researcher_output: str = "",
    writer_output: str = "",
) -> RunResponse:
    final_text = forced_completion_answer(task, researcher_output, writer_output)
    return RunResponse(
        final_result=format_final(final_text),
        activity_history=state.activity_history,
        agent_outputs=state.agent_outputs,
        iterations_used=state.iterations_used,
        forced_completion=True,
    )


def supervisor_delegate(task: str) -> str:
    prompt = (
        "You are the Supervisor agent.\n"
        "Return EXACTLY two lines in this format:\n"
        "DELEGATE: Researcher\n"
        "TASK: <task>\n"
        "Do not add bullets, markdown, or extra text.\n\n"
        f"Task: {task}"
    )
    try:
        raw = openrouter_chat(
            system_prompt="You coordinate a multi-agent workflow and must follow the exact output format.",
            user_prompt=prompt,
        )
        cleaned = normalize_delegate(raw, task)
        if cleaned:
            return cleaned
    except Exception:
        logger.warning("Supervisor delegation fallback engaged", exc_info=True)
    return f"DELEGATE: Researcher\nTASK: {task}"


def researcher_step(task: str, delegate_text: str) -> str:
    prompt = (
        "You are the Researcher agent.\n"
        "Read the task and supervisor instructions, then return concise findings.\n"
        "Focus on concrete observations and useful facts.\n\n"
        f"Task: {task}\n\n"
        f"Supervisor instructions:\n{delegate_text}"
    )
    try:
        return openrouter_chat(
            system_prompt="You are a research agent. Return concise findings only.",
            user_prompt=prompt,
        ).strip() or local_research(task)
    except Exception:
        logger.warning("Researcher fallback engaged", exc_info=True)
        return local_research(task)


def writer_step(task: str, research: str) -> str:
    prompt = (
        "You are the Writer agent.\n"
        "Turn the research findings into a polished response.\n"
        "Keep it clear, direct, and useful.\n\n"
        f"Task: {task}\n\n"
        f"Research findings:\n{research}"
    )
    try:
        return openrouter_chat(
            system_prompt="You are a writing agent. Return a polished response only.",
            user_prompt=prompt,
        ).strip() or local_write(task, research)
    except Exception:
        logger.warning("Writer fallback engaged", exc_info=True)
        return local_write(task, research)


def supervisor_finalize(task: str, research: str, writer_output: str) -> str:
    prompt = (
        "You are the Supervisor agent.\n"
        "Synthesize the final answer from the worker outputs.\n"
        "Return only the answer text, no prefix.\n\n"
        f"Task: {task}\n\n"
        f"Research findings:\n{research}\n\n"
        f"Writer draft:\n{writer_output}"
    )
    try:
        raw = openrouter_chat(
            system_prompt="You are a supervisor. Return a concise final answer only.",
            user_prompt=prompt,
        ).strip()
        return raw or local_final(task, research, writer_output)
    except Exception:
        logger.warning("Supervisor finalization fallback engaged", exc_info=True)
        return local_final(task, research, writer_output)


def forced_completion_answer(task: str, research: str, writer_output: str) -> str:
    summary_source = writer_output or research or task
    return f"Forced completion after reaching max_iterations. {summary_source}".strip()


def local_research(task: str) -> str:
    return f"Key findings: the task is '{task}'. Review the requested topic, identify the main requirements, and summarize the useful facts."


def local_write(task: str, research: str) -> str:
    return f"Polished response for '{task}': {research}"


def local_final(task: str, research: str, writer_output: str) -> str:
    summary = writer_output or research or task
    return f"Final response based on the worker outputs: {summary}"


def format_final(answer: str) -> str:
    cleaned = answer.strip()
    if cleaned.startswith("FINAL:"):
        cleaned = cleaned.removeprefix("FINAL:").strip()
    return f"FINAL: {cleaned}"


def normalize_delegate(raw: str, task: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(lines) >= 2 and lines[0].startswith("DELEGATE:"):
        delegate_line = lines[0]
        task_line = lines[1] if lines[1].startswith("TASK:") else f"TASK: {task}"
        return f"{delegate_line}\n{task_line}"
    return ""


def openrouter_chat(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
    model = os.getenv("OPENAI_MODEL", "google/gemma-4-31b-it:free").strip()
    headers = {"Authorization": f"Bearer {api_key}"}

    http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    title = os.getenv("OPENROUTER_TITLE", "").strip()
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if title:
        headers["X-OpenRouter-Title"] = title

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    with httpx.Client(base_url=base_url, timeout=20.0, headers=headers) as client:
        response = client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("Invalid LLM response")
    return content

