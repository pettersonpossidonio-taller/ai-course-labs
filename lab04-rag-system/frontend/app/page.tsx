"use client";

import { ChangeEvent, FormEvent, useMemo, useState } from "react";

type SourceSnippet = {
  path: string;
  chunk: string;
  score: number;
};

type QueryResponse = {
  answer: string;
  source_snippets: SourceSnippet[];
};

type JudgeResult = {
  score: number;
  details: string;
};

type EvaluateResponse = {
  precision_at_k: number;
  recall_at_k: number;
  mrr: number;
  judge_result: JudgeResult;
};

type IndexResponse = {
  indexed_files: number;
  indexed_chunks: number;
};

type UploadedFile = {
  name: string;
  content: string;
};

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export default function HomePage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string>("");
  const [snippets, setSnippets] = useState<SourceSnippet[]>([]);
  const [metrics, setMetrics] = useState<EvaluateResponse | null>(null);
  const [indexResult, setIndexResult] = useState<IndexResponse | null>(null);
  const [loading, setLoading] = useState<"index" | "query" | "evaluate" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canIndex = useMemo(() => files.length > 0 && loading === null, [files, loading]);
  const canQuery = useMemo(() => question.trim().length > 0 && loading === null, [question, loading]);

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files || []);
    if (selected.length === 0) {
      return;
    }

    try {
      const loaded = await Promise.all(
        selected.map(async (file) => ({
          name: file.name,
          content: await file.text(),
        })),
      );
      setFiles((current) => [...current, ...loaded]);
      setError(null);
    } catch {
      setError("Could not read one or more files.");
    } finally {
      event.target.value = "";
    }
  }

  async function handleIndex(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canIndex) {
      return;
    }

    setLoading("index");
    setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/index/files`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files: files.map((file) => ({ path: file.name, content: file.content })),
        }),
      });
      const data = (await response.json()) as IndexResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(data && "detail" in data && data.detail ? data.detail : "Indexing failed");
      }
      setIndexResult(data as IndexResponse);
      setAnswer("");
      setSnippets([]);
      setMetrics(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Indexing failed");
    } finally {
      setLoading(null);
    }
  }

  async function handleQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canQuery) {
      return;
    }

    setLoading("query");
    setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 3 }),
      });
      const data = (await response.json()) as QueryResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(data && "detail" in data && data.detail ? data.detail : "Query failed");
      }
      const body = data as QueryResponse;
      setAnswer(body.answer);
      setSnippets(body.source_snippets);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(null);
    }
  }

  async function handleEvaluate() {
    setLoading("evaluate");
    setError(null);
    setMetrics(null);
    try {
      const response = await fetch(`${apiBaseUrl}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ top_k: 3 }),
      });
      const data = (await response.json()) as EvaluateResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(data && "detail" in data && data.detail ? data.detail : "Evaluation failed");
      }
      setMetrics(data as EvaluateResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Lab 04</p>
          <h1>RAG System</h1>
          <p className="lead">
            Upload code files, index them, ask questions, and review source-grounded answers.
          </p>
        </div>

        <div className="workspace">
          <section className="panel">
            <h2>Indexing</h2>
            <form className="stack" onSubmit={handleIndex}>
              <label className="field">
                <span>File Upload</span>
                <input type="file" multiple onChange={handleFileUpload} />
              </label>

              <div className="file-list">
                {files.length > 0 ? files.map((file) => <div key={file.name}>{file.name}</div>) : <p className="muted">No files selected.</p>}
              </div>

              <button type="submit" disabled={!canIndex}>
                {loading === "index" ? "Indexing..." : "Index Files"}
              </button>

              {indexResult ? (
                <p className="muted">
                  Indexed {indexResult.indexed_files} files and {indexResult.indexed_chunks} chunks.
                </p>
              ) : null}
            </form>
          </section>

          <section className="panel">
            <h2>Querying</h2>
            <form className="stack" onSubmit={handleQuery}>
              <label className="field">
                <span>Question</span>
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="How does authentication work?"
                  rows={5}
                />
              </label>
              <button type="submit" disabled={!canQuery}>
                {loading === "query" ? "Searching..." : "Ask Question"}
              </button>
            </form>
          </section>

          <section className="panel">
            <h2>Answer</h2>
            {answer ? <p className="answer-text">{answer}</p> : <p className="muted">No answer yet.</p>}
          </section>

          <section className="panel">
            <h2>Source Snippets</h2>
            {snippets.length > 0 ? (
              <div className="snippet-list">
                {snippets.map((snippet, index) => (
                  <article className="snippet" key={`${snippet.path}-${index}`}>
                    <div className="snippet-topline">
                      <strong>{snippet.path}</strong>
                      <span>{snippet.score.toFixed(3)}</span>
                    </div>
                    <pre>{snippet.chunk}</pre>
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted">No snippets yet.</p>
            )}
          </section>

          <section className="panel">
            <h2>Evaluation Metrics</h2>
            <button type="button" onClick={handleEvaluate} disabled={loading !== null || files.length === 0}>
              {loading === "evaluate" ? "Evaluating..." : "Run Evaluation"}
            </button>
            {metrics ? (
              <div className="metrics-grid">
                <div><span>Precision@K</span><strong>{metrics.precision_at_k}</strong></div>
                <div><span>Recall@K</span><strong>{metrics.recall_at_k}</strong></div>
                <div><span>MRR</span><strong>{metrics.mrr}</strong></div>
                <div><span>Judge</span><strong>{metrics.judge_result.score}</strong><p>{metrics.judge_result.details}</p></div>
              </div>
            ) : (
              <p className="muted">No evaluation yet.</p>
            )}
          </section>

          {error ? <section className="panel error-panel"><h2>Error</h2><p>{error}</p></section> : null}
        </div>
      </section>
    </main>
  );
}
