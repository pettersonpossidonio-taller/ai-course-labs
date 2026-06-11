"use client";

import { ChangeEvent, FormEvent, useMemo, useState } from "react";

type Severity = "high" | "medium" | "low";

type Issue = {
  severity: Severity;
  line: number;
  category: "bug" | "security" | "performance" | "style" | "maintainability";
  description: string;
  suggestion: string;
};

type AnalysisResponse = {
  summary: string;
  issues: Issue[];
  suggestions: string[];
  metrics: {
    complexity: string;
    readability: string;
    test_coverage_estimate: string;
  };
};

type AnalysisMode = "general" | "security";
type Language = "python" | "typescript" | "javascript" | "go" | "java";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

const severityLabels: Record<Severity, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

const languageOptions: Array<{ value: Language; label: string }> = [
  { value: "python", label: "Python" },
  { value: "typescript", label: "TypeScript" },
  { value: "javascript", label: "JavaScript" },
  { value: "go", label: "Go" },
  { value: "java", label: "Java" },
];

export default function HomePage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState<Language>("python");
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("general");
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const canAnalyze = useMemo(() => code.trim().length > 0 && !isLoading, [code, isLoading]);

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const text = await file.text();
      setCode(text);
      setFileName(file.name);
      setError(null);
      setResult(null);
    } catch {
      setError("Could not read the selected file.");
    } finally {
      event.target.value = "";
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${apiBaseUrl}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          code,
          language,
          analysis_mode: analysisMode,
        }),
      });

      const data = (await response.json()) as AnalysisResponse | { detail?: string };

      if (!response.ok) {
        throw new Error(data && "detail" in data && data.detail ? data.detail : "Analysis failed");
      }

      setResult(data as AnalysisResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Lab 02</p>
          <h1>Code Analyzer</h1>
          <p className="lead">
            Paste code or upload a file, choose an analysis mode, and review the structured feedback.
          </p>
        </div>

        <div className="workspace">
          <form className="editor-panel" onSubmit={handleSubmit}>
            <div className="toolbar">
              <label className="field">
                <span>Language</span>
                <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
                  {languageOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Analysis Mode</span>
                <select value={analysisMode} onChange={(event) => setAnalysisMode(event.target.value as AnalysisMode)}>
                  <option value="general">General</option>
                  <option value="security">Security</option>
                </select>
              </label>

              <label className="upload-button">
                <span>Upload File</span>
                <input type="file" onChange={handleFileUpload} />
              </label>
            </div>

            <label className="field editor-field">
              <span>Code</span>
              <textarea
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="Paste your code here..."
                rows={18}
              />
            </label>

            <div className="actions">
              <button type="submit" disabled={!canAnalyze}>
                {isLoading ? "Analyzing..." : "Analyze"}
              </button>
              {fileName ? <p className="file-name">Loaded: {fileName}</p> : null}
            </div>

            {error ? <p className="error">{error}</p> : null}
          </form>

          <aside className="results-panel" aria-live="polite">
            <div className="results-header">
              <h2>Results</h2>
              <p>{apiBaseUrl}</p>
            </div>

            {result ? (
              <div className="results-grid">
                <section className="result-block">
                  <h3>Summary</h3>
                  <p>{result.summary}</p>
                </section>

                <section className="result-block">
                  <h3>Issues</h3>
                  {result.issues.length > 0 ? (
                    <ul className="issue-list">
                      {result.issues.map((issue, index) => (
                        <li key={`${issue.line}-${issue.category}-${index}`} className={`issue severity-${issue.severity}`}>
                          <div className="issue-topline">
                            <strong>
                              {severityLabels[issue.severity]} severity
                            </strong>
                            <span>
                              Line {issue.line} · {issue.category}
                            </span>
                          </div>
                          <p>{issue.description}</p>
                          <p className="suggestion">
                            <span>Suggestion:</span> {issue.suggestion}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No issues found.</p>
                  )}
                </section>

                <section className="result-block">
                  <h3>Suggestions</h3>
                  {result.suggestions.length > 0 ? (
                    <ul className="bullets">
                      {result.suggestions.map((item, index) => (
                        <li key={`${item}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No suggestions returned.</p>
                  )}
                </section>

                <section className="result-block metrics">
                  <h3>Metrics</h3>
                  <dl>
                    <div>
                      <dt>Complexity</dt>
                      <dd>{result.metrics.complexity}</dd>
                    </div>
                    <div>
                      <dt>Readability</dt>
                      <dd>{result.metrics.readability}</dd>
                    </div>
                    <div>
                      <dt>Test coverage estimate</dt>
                      <dd>{result.metrics.test_coverage_estimate}</dd>
                    </div>
                  </dl>
                </section>
              </div>
            ) : (
              <div className="empty-state">
                <p>No analysis yet.</p>
                <p>Enter code, choose a mode, and run analysis.</p>
              </div>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

