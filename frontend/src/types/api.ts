export type Mode = "auto" | "answer" | "explain" | "show_me" | "solve_with_me";
export type Project = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  has_thumbnail: boolean;
};
export type CanvasFile = {
  id: string;
  mimeType: string;
  created: number;
  dataURL?: string;
  [key: string]: unknown;
};
export type CanvasLoad = {
  elements: readonly Record<string, unknown>[];
  app_state: Record<string, unknown>;
  files: Record<string, CanvasFile>;
};
export type Target =
  | { x: number; y: number }
  | {
      element_id: string;
      region?: [number, number, number, number];
      text?: string;
    };
export type CanvasAction =
  | {
      tool: "write_text";
      text: string;
      near?: Target;
      side?: "right" | "left" | "above" | "below";
      size?: "s" | "m" | "l";
      color?: string;
    }
  | {
      tool: "draw_arrow" | "draw_line";
      start: Target;
      end: Target;
      label?: string;
      color?: string;
    }
  | {
      tool: "draw_rectangle" | "draw_circle" | "highlight";
      target: Target;
      padding?: number;
      label?: string;
      color?: string;
    }
  | { tool: "point_to"; target: Target; label?: string }
  | { tool: "zoom_to"; target: Target }
  | { tool: "delete_ai_element"; element_id: string };
export type Step = {
  say?: string;
  actions: CanvasAction[];
  wait_for_student: boolean;
  question?: string;
};
export type AIEvent =
  | { type: "status"; message: string }
  | { type: "step"; index: number; step: Step }
  | { type: "warning"; message: string }
  | { type: "done"; action_id: string; steps: number; text: string }
  | { type: "error"; code: string; message: string };
