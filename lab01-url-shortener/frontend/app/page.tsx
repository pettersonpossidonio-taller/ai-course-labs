"use client";

import { FormEvent, useState } from "react";

type ShortenResponse = {
  short_code: string;
  short_url: string;
};

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export default function HomePage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const [url, setUrl] = useState("");
  const [shortened, setShortened] = useState<ShortenResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setShortened(null);
    setCopyState("idle");

    try {
      const response = await fetch(`${apiBaseUrl}/shorten`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      const data = (await response.json()) as ShortenResponse | { detail?: string };

      if (!response.ok) {
        const errorData = data as { detail?: string };
        throw new Error(errorData.detail || "Unable to shorten URL");
      }

      setShortened(data as ShortenResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to shorten URL");
    } finally {
      setIsLoading(false);
    }
  }

  async function copyShortUrl() {
    if (!shortened) {
      return;
    }

    try {
      await navigator.clipboard.writeText(shortened.short_url);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1500);
    } catch {
      setError("Could not copy the short URL");
    }
  }

  return (
    <main className="page-shell">
      <section className="panel">
        <div className="stack">
          <h1>URL Shortener</h1>
          <p>Enter a long URL, generate a short link, and copy it.</p>
        </div>

        <form className="form" onSubmit={onSubmit}>
          <label className="field">
            <span>Long URL</span>
            <input
              type="url"
              placeholder="https://example.com/article"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
            />
          </label>

          <button type="submit" disabled={isLoading}>
            {isLoading ? "Shortening..." : "Shorten URL"}
          </button>
        </form>

        {error ? <p className="error">{error}</p> : null}

        {shortened ? (
          <div className="result" aria-live="polite">
            <label className="field">
              <span>Short URL</span>
              <input readOnly value={shortened.short_url} />
            </label>
            <button type="button" onClick={copyShortUrl}>
              {copyState === "copied" ? "Copied" : "Copy"}
            </button>
          </div>
        ) : null}

        <p className="hint">Backend API: {apiBaseUrl}</p>
      </section>
    </main>
  );
}
