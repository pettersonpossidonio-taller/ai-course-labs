"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";

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

type LanguageIconConfig = {
  label: string;
  src?: string;
  alt?: string;
  fallbackLabel: string;
};

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

const languageIcons: Record<Language, LanguageIconConfig> = {
  python: {
    label: "Python",
    src: "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/python/python-original.svg",
    alt: "Python logo",
    fallbackLabel: "Py",
  },
  typescript: {
    label: "TypeScript",
    src: "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/typescript/typescript-original.svg",
    alt: "TypeScript logo",
    fallbackLabel: "TS",
  },
  javascript: {
    label: "JavaScript",
    src: "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/javascript/javascript-original.svg",
    alt: "JavaScript logo",
    fallbackLabel: "JS",
  },
  go: {
    label: "Go",
    src: "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/go/go-original.svg",
    alt: "Go logo",
    fallbackLabel: "Go",
  },
  java: {
    label: "Java",
    src: "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/java/java-original.svg",
    alt: "Java logo",
    fallbackLabel: "Ja",
  },
};

const sampleCode = `def calculate_discount(price, percent):
    discount = price * percent / 100
    return price - discount

def apply_coupon(price, coupon):
    if coupon == "SUMMER":
        return price * 0.9
    return price
`;

function CodeIcon() {
  return (
    <svg className="code-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M6.22 4.22a.75.75 0 0 1 1.06 1.06L5.56 7l1.72 1.72a.75.75 0 1 1-1.06 1.06l-2.25-2.25a.75.75 0 0 1 0-1.06l2.25-2.25Zm3.56 0a.75.75 0 0 1 0 1.06L8.06 7l1.72 1.72a.75.75 0 1 1-1.06 1.06L6.47 7.53a.75.75 0 0 1 0-1.06l2.25-2.25a.75.75 0 0 1 1.06 0Z" />
    </svg>
  );
}

function LanguageLogo({ language }: { language: Language }) {
  const config = languageIcons[language];
  if (config.src) {
    return <img className="language-logo" src={config.src} alt={config.alt || config.label} width={24} height={24} />;
  }

  return (
    <span className="language-logo fallback" aria-hidden="true">
      <CodeIcon />
    </span>
  );
}

function LanguageDropdown({
  language,
  onChange,
}: {
  language: Language;
  onChange: (nextLanguage: Language) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  const selected = languageIcons[language];

  return (
    <div className="language-dropdown" ref={rootRef}>
      <button
        type="button"
        className="language-trigger"
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="language-trigger-main">
          <LanguageLogo language={language} />
          <span className="language-trigger-text">
            <span className="language-trigger-label">Language Selector</span>
            <span className="language-trigger-value">{selected.label}</span>
          </span>
        </span>
        <span className="language-trigger-caret" aria-hidden="true">
          ▾
        </span>
      </button>

      {open ? (
        <div className="language-menu" role="listbox" aria-label="Language Selector">
          {languageOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              role="option"
              aria-selected={language === option.value}
              className={`language-option ${language === option.value ? "is-selected" : ""}`}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              <LanguageLogo language={option.value} />
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Spinner() {
  return (
    <svg className="spinner" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <circle cx="8" cy="8" r="6" />
    </svg>
  );
}

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
            Analyze source code with AI-powered code review. Detect bugs, security risks, performance issues, and maintainability concerns.
          </p>
        </header>

        <div className="workspace">
          <form className="editor-panel" onSubmit={handleAnalyze}>
            <div className="controls-stack">
              <LanguageDropdown language={language} onChange={setLanguage} />

              <label className="field upload-field">
                <span>File Upload</span>
                <div className="upload-row">
                  <input type="file" onChange={handleFileUpload} />
                  <p className="file-name file-name-inline">{fileName ? `Loaded: ${fileName}` : "No file loaded yet."}</p>
                </div>
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
              <button className={`primary-button ${loading ? "is-loading" : ""}`} type="submit" disabled={!canAnalyze}>
                {loading ? (
                  <span className="button-content">
                    <Spinner />
                    Analyzing...
                  </span>
                ) : (
                  "Analyze Code"
                )}
              </button>
            </div>

            {error ? <p className="error">{error}</p> : null}
          </form>

          <section className="results-grid">
            <article className="panel summary-panel">
              <h2>Executive Summary</h2>
              {result ? <p className="summary-text">{result.summary}</p> : <p className="muted">Submit code to generate an AI review.</p>}
            </article>

            <article className="panel risk-panel">
              <h2>Risk Level</h2>
              {result ? <span className={`risk-badge risk-${result.risk_level.toLowerCase()}`}>{result.risk_level}</span> : <p className="muted">Risk assessment will appear here.</p>}
            </article>

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
                <p className="muted">Findings will be grouped by category and severity.</p>
              )}
            </section>
          </section>
        </div>
      </section>
    </main>
  );
}
