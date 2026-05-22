/**
 * API base URL for rhythm analysis.
 * - Dev: leave VITE_API_URL unset; Vite proxies /analyze and /health to localhost:8000.
 * - Production (Render static site): set VITE_API_URL at build time to your backend URL.
 */
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

const ANALYZE_TIMEOUT_MS = Number(import.meta.env.VITE_ANALYZE_TIMEOUT_MS || 120000);

export function getApiBase() {
  return API_BASE;
}

export function isApiConfigured() {
  return Boolean(API_BASE);
}

/** In production builds, the API URL must be baked in at build time. */
export function resolveAnalyzeUrl() {
  if (import.meta.env.PROD && !API_BASE) {
    throw new Error(
      'Analysis API is not configured. On Render, set VITE_API_URL on the static site ' +
        '(e.g. https://your-api.onrender.com) and redeploy the frontend.'
    );
  }
  return `${API_BASE}/analyze`;
}

export function resolveHealthUrl() {
  if (import.meta.env.PROD && !API_BASE) {
    return null;
  }
  return `${API_BASE}/health`;
}

export async function fetchWithTimeout(url, options = {}, timeoutMs = ANALYZE_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

export function parseApiError(response, data) {
  if (response.status === 502) {
    return (
      'The server stopped or timed out while analyzing. Use a clip under 25 seconds, ' +
      'or upgrade your Render API plan for longer videos.'
    );
  }
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail) return JSON.stringify(detail);
  return `Analysis failed (${response.status}).`;
}

/** Reject HTML/error pages that were mis-routed to the static frontend. */
export function assertAnalysisPayload(data) {
  if (!data || typeof data !== 'object' || !('valid_video' in data)) {
    throw new Error(
      'The server returned an invalid response. If this site is on Render, confirm ' +
        'VITE_API_URL points to your Python API (not this static site URL).'
    );
  }
  return data;
}
