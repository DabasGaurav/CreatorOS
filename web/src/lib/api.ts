import type { Creator, CreatorDNA, Recommendation } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(body || response.statusText, response.status);
  }
  return response.json() as Promise<T>;
}

export function createRecommendation(
  creatorId: string,
  objective = "grow reach",
): Promise<{ request_id: string; status: string }> {
  return request("/recommendations", {
    method: "POST",
    body: JSON.stringify({ creator_id: creatorId, objective }),
  });
}

export function getRecommendation(requestId: string): Promise<Recommendation> {
  return request(`/recommendations/${requestId}`);
}

export function getCreator(creatorId: string): Promise<Creator & { dna: CreatorDNA | null }> {
  return request(`/creators/${creatorId}`);
}
