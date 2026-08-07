import type { ReviewCase, ReviewDecisionRequest } from "../types/review";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getGoldenReviewCase(): Promise<ReviewCase> {
  return request<ReviewCase>("/api/v1/review-cases/golden");
}

export function submitReviewDecision(
  decision: ReviewDecisionRequest["decision"],
  comment: string
): Promise<ReviewCase> {
  return request<ReviewCase>("/api/v1/review-cases/golden/decision", {
    method: "POST",
    body: JSON.stringify({ decision, comment })
  });
}
