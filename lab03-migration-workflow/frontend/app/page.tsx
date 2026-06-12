"use client";

import { ChangeEvent, FormEvent, useMemo, useState } from "react";

type PhaseName = "analysis" | "planning" | "execution" | "verification";
type StepStatus = "pending" | "in_progress" | "completed" | "failed";

type PlanStep = {
  phase: PhaseName;
  description: string;
  dependencies: PhaseName[];
  status: StepStatus;
};

type MigratedFile = {
  path: string;
  content: string;
};

type VerificationResult = {
  success: boolean;
  details: string;
};

type MigrationResponse = {
  success: boolean;
  migrated_files: MigratedFile[];
  executed_plan: PlanStep[];
  verification_result: VerificationResult;
  errors: string[];
};

type FrameworkName = "fastapi" | "flask";

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const phases: PhaseName[] = ["analysis", "planning", "execution", "verification"];
const frameworkOptions: Array<{ value: FrameworkName; label: string }> = [
  { value: "fastapi", label: "FastAPI" },
  { value: "flask", label: "Flask" },
];

export default function HomePage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const [sourceFramework, setSourceFramework] = useState<FrameworkName>("fastapi");
  const [targetFramework, setTargetFramework] = useState<FrameworkName>("flask");
  const [sourceText, setSourceText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<PhaseName | null>(null);
  const [result, setResult] = useState<MigrationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const canSubmit = useMemo(() => sourceText.trim().length > 0 && !isLoading, [sourceText, isLoading]);

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const text = await file.text();
      setSourceText(text);
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
    setCurrentPhase("analysis");

    const sourceFileName = fileName || `app.${sourceFramework === "fastapi" ? "py" : "py"}`;

    try {
      setCurrentPhase("analysis");
      const response = await fetch(`${apiBaseUrl}/migrate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_framework: sourceFramework,
          target_framework: targetFramework,
          source_files: [
            {
              path: sourceFileName,
              content: sourceText,
            },
          ],
        }),
      });

      const data = (await response.json()) as MigrationResponse | { detail?: string };

      if (!response.ok) {
        throw new Error(data && "detail" in data && data.detail ? data.detail : "Migration failed");
      }

      setCurrentPhase("planning");
      setCurrentPhase("execution");
      setCurrentPhase("verification");
      setResult(data as MigrationResponse);
      setCurrentPhase(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Migration failed");
      setCurrentPhase(null);
    } finally {
      setIsLoading(false);
    }
  }

  const migratedText = result?.migrated_files?.[0]?.content || "";
  const originalText = sourceText;
  const executedPlan = result?.executed_plan || [];
  const verification = result?.verification_result || null;
  const diffLines = useMemo(() => {
    const originalLines = originalText.split(/\r?\n/);
    const migratedLines = migratedText.split(/\r?\n/);
    const maxLength = Math.max(originalLines.length, migratedLines.length);
    return Array.from({ length: maxLength }, (_, index) => ({
      original: originalLines[index] ?? "",
      migrated: migratedLines[index] ?? "",
      index,
    }));
  }, [originalText, migratedText]);

  return (
    <main className="page-shell">
      <section className="app-shell">
        <header className="hero-copy">
          <p className="eyebrow">Lab 03</p>
          <h1>Migration Workflow</h1>
          <p className="lead">Upload source code, choose frameworks, and run a minimal migration workflow.</p>
        </header>

        <form className="control-panel" onSubmit={handleSubmit}>
          <label className="field">
            <span>File Upload</span>
            <input type="file" onChange={handleFileUpload} />
          </label>

          <div className="toolbar">
            <label className="field">
              <span>Source Framework</span>
              <select value={sourceFramework} onChange={(event) => setSourceFramework(event.target.value as FrameworkName)}>
                {frameworkOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Target Framework</span>
              <select value={targetFramework} onChange={(event) => setTargetFramework(event.target.value as FrameworkName)}>
                {frameworkOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="field">
            <span>Source Code</span>
            <textarea value={sourceText} onChange={(event) => setSourceText(event.target.value)} rows={14} placeholder="Upload a file or paste source code here." />
          </label>

          <button type="submit" disabled={!canSubmit}>
            {isLoading ? "Migrating..." : "Migrate"}
          </button>
        </form>

        <section className="panel">
          <h2>Current Phase</h2>
          <div className="phase-track">
            {phases.map((phase) => (
              <span key={phase} className={phase === currentPhase ? "phase active" : "phase"}>
                {phase}
              </span>
            ))}
          </div>
          <p className="muted">{currentPhase ?? (result?.success ? "verification" : "idle")}</p>
        </section>

        <section className="panel">
          <h2>Migration Plan</h2>
          {executedPlan.length > 0 ? (
            <div className="plan-list">
              {executedPlan.map((step) => (
                <div key={step.phase} className={`plan-step status-${step.status}`}>
                  <div className="plan-topline">
                    <strong>{step.phase}</strong>
                    <span>{step.status}</span>
                  </div>
                  <p>{step.description}</p>
                  <p className="muted">Dependencies: {step.dependencies.length > 0 ? step.dependencies.join(", ") : "none"}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">No migration plan yet.</p>
          )}
        </section>

        <section className="split-grid">
          <section className="panel">
            <h2>Migrated Output</h2>
            {migratedText ? <pre className="code-block">{migratedText}</pre> : <p className="muted">No migrated code yet.</p>}
          </section>

          <section className="panel">
            <h2>Diff View</h2>
            {diffLines.length > 0 ? (
              <div className="diff-list">
                {diffLines.map((line) => (
                  <div key={line.index} className="diff-row">
                    <pre className="diff-cell original">{line.original || " "}</pre>
                    <pre className="diff-cell migrated">{line.migrated || " "}</pre>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">No diff available yet.</p>
            )}
          </section>
        </section>

        <section className="panel">
          <h2>Verification Result</h2>
          {verification ? <p>{verification.success ? "Passed" : "Failed"}: {verification.details}</p> : <p className="muted">No verification result yet.</p>}
        </section>

        <section className="panel">
          <h2>Errors</h2>
          {error ? <p className="error">{error}</p> : result?.errors?.length ? <ul className="error-list">{result.errors.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">No errors.</p>}
        </section>
      </section>
    </main>
  );
}
