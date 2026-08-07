import type { ReviewCase, ReviewDecisionRequest } from "../types/review";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: isFormData
      ? init?.headers
      : {
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

export function getReviewCase(caseId: string): Promise<ReviewCase> {
  return request<ReviewCase>(`/api/v1/review-cases/${caseId}`);
}

export function submitReviewDecision(
  caseId: string,
  decision: ReviewDecisionRequest["decision"],
  comment: string
): Promise<ReviewCase> {
  return request<ReviewCase>(`/api/v1/review-cases/${caseId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, comment })
  });
}

export function processReviewDocuments(invoice: File, remittance: File): Promise<ReviewCase> {
  const formData = new FormData();
  formData.append("invoice", invoice);
  formData.append("remittance", remittance);
  return request<ReviewCase>("/api/v1/reconciliation/process", {
    method: "POST",
    body: formData
  });
}

export function processSampleDocuments(): Promise<ReviewCase> {
  const formData = new FormData();
  formData.append("use_sample", "true");
  return request<ReviewCase>("/api/v1/reconciliation/process", {
    method: "POST",
    body: formData
  });
}
