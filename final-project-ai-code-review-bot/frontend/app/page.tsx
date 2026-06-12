"use client";

import { ChangeEvent, FormEvent, useMemo, useState } from "react";

type Severity = "Critical" | "High" | "Medium" | "Low";

type Finding = {
  category: "Bug" | "Security" | "Performance" | "Style" | "Maintainability";
  severity: Severity;
  title: string;
  description: string;
  recommendation: string;
};

type AnalyzeResponse = {
  summary: string;
  risk_level: "Low" | "Medium" | "High";
  findings: Finding[];
};

type Language = "python" | "typescript" | "javascript" | "go" | "java";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

const severityLabels: Record<Severity, string> = {
  Critical: "Critical",
  High: "High",
  Medium: "Medium",
  Low: "Low",
};

const languageOptions: Array<{ value: Language; label: string }> = [
  { value: "python", label: "Python" },
  { value: "typescript", label: "TypeScript" },
  { value: "javascript", label: "JavaScript" },
  { value: "go", label: "Go" },
  { value: "java", label: "Java" },
];

const sampleCode = `def calculate_discount(price, percent):
    discount = price * percent / 100
    return price - discount

def apply_coupon(price, coupon):
    if coupon == "SUMMER":
        return price * 0.9
    return price
`;

export default function HomePage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const [code, setCode] = useState(sampleCode);
  const [language, setLanguage] = useState<Language>("python");
  const [fileName, setFileName] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canAnalyze = useMemo(() => code.trim().length > 0 && !loading, [code, loading]);

  const groupedFindings = useMemo(() => {
    const groups: Record<Finding["category"], Finding[]> = {
      Bug: [],
      Security: [],
      Performance: [],
      Style: [],
      Maintainability: [],
    };

    for (const finding of result?.findings ?? []) {
      groups[finding.category].push(finding);
    }

    return groups;
  }, [result]);

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      setCode(await file.text());
      setFileName(file.name);
      setError(null);
      setResult(null);
    } catch {
      setError("Could not read the selected file.");
    } finally {
      event.target.value = "";
    }
  }

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canAnalyze) {
      return;
    }

    setLoading(true);
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
        }),
      });

      const data = (await response.json()) as AnalyzeResponse | { detail?: string; error?: string };

      if (!response.ok) {
        const message = "detail" in data ? data.detail : "error" in data ? data.error : undefined;
        throw new Error(message || "Analysis failed");
      }

      setResult(data as AnalyzeResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <header className="hero-copy">
          <p className="eyebrow">Final Project</p>
          <h1>AI Code Review Bot</h1>
          <p className="lead">
            Paste code or upload a file, choose a language, and get a professional review backed by OpenRouter.
          </p>
        </header>

        <div className="workspace">
          <section className="panel panel-header">
            <div className="header-grid">
              <div>
                <h2>Project Header</h2>
                <p className="muted">Standalone FastAPI + Next.js code review workflow.</p>
              </div>
              <div className="info-pill">
                <span>Backend</span>
                <strong>Railway</strong>
              </div>
              <div className="info-pill">
                <span>Frontend</span>
                <strong>Vercel</strong>
              </div>
            </div>
          </section>

          <form className="panel editor-panel" onSubmit={handleAnalyze}>
            <div className="toolbar">
              <label className="field">
                <span>Language Selector</span>
                <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
                  {languageOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field upload">
                <span>File Upload</span>
                <input type="file" onChange={handleFileUpload} />
              </label>
            </div>

            <label className="field editor-field">
              <span>Code Input</span>
              <textarea
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="Paste source code here..."
                rows={18}
              />
            </label>

            <div className="actions">
              <button type="submit" disabled={!canAnalyze}>
                {loading ? "Analyzing..." : "Analyze Code"}
              </button>
              {fileName ? <p className="file-name">Loaded: {fileName}</p> : <p className="file-name">Sample code loaded.</p>}
            </div>

            {error ? <p className="error">{error}</p> : null}
          </form>

          <section className="panel summary-panel">
            <h2>Executive Summary</h2>
            {result ? <p className="summary-text">{result.summary}</p> : <p className="muted">No analysis yet.</p>}
          </section>

          <section className="panel risk-panel">
            <h2>Risk Level</h2>
            {result ? <span className={`risk-badge risk-${result.risk_level.toLowerCase()}`}>{result.risk_level}</span> : <p className="muted">No risk level yet.</p>}
          </section>

          <section className="panel findings-panel">
            <h2>Findings Dashboard</h2>
            {result ? (
              <div className="finding-groups">
                {(Object.keys(groupedFindings) as Array<Finding["category"]>).map((category) => (
                  <section key={category} className="finding-group">
                    <div className="group-header">
                      <h3>{category}</h3>
                      <span>{groupedFindings[category].length}</span>
                    </div>

                    {groupedFindings[category].length > 0 ? (
                      <div className="finding-list">
                        {groupedFindings[category].map((finding, index) => (
                          <article className="finding-card" key={`${category}-${index}`}>
                            <div className="finding-topline">
                              <strong>{finding.title}</strong>
                              <span className={`severity-badge severity-${finding.severity.toLowerCase()}`}>
                                {severityLabels[finding.severity]}
                              </span>
                            </div>
                            <p>{finding.description}</p>
                            <div className="recommendation">
                              <span>Recommendation</span>
                              <p>{finding.recommendation}</p>
                            </div>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="muted">No findings in this category.</p>
                    )}
                  </section>
                ))}
              </div>
            ) : (
              <p className="muted">Run an analysis to view categorized findings.</p>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

