import type { CanvasLoad, Project } from "@/types/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public code = "request_failed",
  ) {
    super(message);
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let body: { error?: { code?: string; message?: string } } = {};
    try {
      body = (await response.json()) as typeof body;
    } catch {
      /* no body */
    }
    throw new ApiError(
      body.error?.message ?? `Request failed (${response.status}).`,
      body.error?.code,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () =>
    request<{
      ok: boolean;
      groq_configured: boolean;
      sarvam_configured: boolean;
      storage: string;
    }>("/api/health"),
  listProjects: () => request<Project[]>("/api/projects"),
  getProject: (id: string) => request<Project>(`/api/projects/${id}`),
  createProject: (title: string) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  renameProject: (id: string, title: string) =>
    request<Project>(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteProject: (id: string) =>
    request<void>(`/api/projects/${id}`, { method: "DELETE" }),
  loadCanvas: (id: string) => request<CanvasLoad>(`/api/projects/${id}/canvas`),
  saveCanvas: (id: string, body: unknown) =>
    request<{ updated_at: string }>(`/api/projects/${id}/canvas`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  transcribe: async (blob: Blob, language: string) => {
    const form = new FormData();
    form.append("file", blob, "recording.wav");
    form.append("language", language);
    const response = await fetch("/api/transcribe", {
      method: "POST",
      body: form,
    });
    if (!response.ok)
      throw new ApiError("Couldn't hear that. Try again or type it.");
    return response.json() as Promise<{
      transcript: string;
      language_code: string;
      provider: string;
    }>;
  },
  speak: (text: string, language?: string) =>
    request<{ audio_base64: string; mime: string }>("/api/speak", {
      method: "POST",
      body: JSON.stringify({ text, language_code: language }),
    }),
};
