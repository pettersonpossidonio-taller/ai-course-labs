"use client";

import { FormEvent, useMemo, useState } from "react";

type ActivityEntry = {
  step: number;
  agent: "Supervisor" | "Researcher" | "Writer";
  content: string;
};

type AgentOutput = {
  agent: "Supervisor" | "Researcher" | "Writer";
  output: string;
};

type RunResponse = {
  final_result: string;
  activity_history: ActivityEntry[];
  agent_outputs: AgentOutput[];
  iterations_used: number;
  forced_completion: boolean;
};

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export default function HomePage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const [task, setTask] = useState("");
  const [maxIterations, setMaxIterations] = useState(5);
  const [result, setResult] = useState<RunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canRun = useMemo(() => task.trim().length > 0 && !loading, [task, loading]);

  async function handleRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canRun) {
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${apiBaseUrl}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task,
          max_iterations: maxIterations,
        }),
      });
      const data = (await response.json()) as RunResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(data && "detail" in data && data.detail ? data.detail : "Run failed");
      }
      setResult(data as RunResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Lab 05</p>
          <h1>Multi-Agent Orchestration</h1>
          <p className="lead">
            Submit a task, watch the supervisor delegate work, and review the final synthesized answer.
          </p>
        </div>

        <div className="workspace">
          <section className="panel panel-hero">
            <form className="stack" onSubmit={handleRun}>
              <label className="field">
                <span>Task</span>
                <textarea
                  value={task}
                  onChange={(event) => setTask(event.target.value)}
                  placeholder="Research a topic, synthesize findings, and produce a polished response."
                  rows={6}
                />
              </label>

              <label className="field compact">
                <span>Max Iterations</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={maxIterations}
                  onChange={(event) => setMaxIterations(Number(event.target.value) || 1)}
                />
              </label>

              <button type="submit" disabled={!canRun}>
                {loading ? "Running..." : "Run Workflow"}
              </button>
            </form>
          </section>

          <section className="panel">
            <h2>Activity Feed</h2>
            {result?.activity_history?.length ? (
              <div className="stack">
                {result.activity_history.map((entry) => (
                  <article className="timeline-item" key={`${entry.step}-${entry.agent}`}>
                    <div className="timeline-topline">
                      <strong>
                        Step {entry.step} · {entry.agent}
                      </strong>
                    </div>
                    <p>{entry.content}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted">No activity yet.</p>
            )}
          </section>

          <section className="panel">
            <h2>Conversation History</h2>
            {result?.agent_outputs?.length ? (
              <div className="stack">
                {result.agent_outputs.map((entry, index) => (
                  <article className="history-item" key={`${entry.agent}-${index}`}>
                    <div className="timeline-topline">
                      <strong>{entry.agent}</strong>
                    </div>
                    <pre>{entry.output}</pre>
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted">No conversation history yet.</p>
            )}
          </section>

          <section className="panel panel-output">
            <h2>Final Output</h2>
            {result ? (
              <div className="output-card">
                <p className="muted">
                  Iterations used: {result.iterations_used} · Forced completion: {result.forced_completion ? "Yes" : "No"}
                </p>
                <pre>{result.final_result}</pre>
              </div>
            ) : (
              <p className="muted">No final result yet.</p>
            )}
          </section>

          {error ? (
            <section className="panel error-panel">
              <h2>Error</h2>
              <p>{error}</p>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}

