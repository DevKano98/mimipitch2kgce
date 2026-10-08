import {
  CaptureUpdateAction,
  convertToExcalidrawElements,
} from "@excalidraw/excalidraw";
import type { CanvasAction } from "@/types/api";
import { colors } from "@/services/colors";
import {
  center,
  clipLine,
  freeSpace,
  resolveRect,
  type OcrWord,
  type Rect,
} from "@/services/targets";

const tag = (items: any[], actionId: string, step: number) =>
  items.map((item) => ({
    ...item,
    customData: {
      ...(item.customData ?? {}),
      createdBy: "ai",
      actionId,
      step,
      createdVersion: item.version,
    },
  }));
const rects = (items: readonly any[]): Rect[] =>
  items
    .filter((e) => !e.isDeleted)
    .map((e) => ({ x: e.x, y: e.y, width: e.width, height: e.height }));
export async function executeAction(
  api: any,
  action: CanvasAction,
  actionId: string,
  step: number,
  onPoint: (p: { x: number; y: number } | null) => void,
  followAI = true,
  ocr: Record<string, OcrWord[]> = {},
): Promise<string[]> {
  const existing = api.getSceneElements();
  const resolve = (t: any) => resolveRect(t, existing, ocr);
  const created: string[] = [];
  let skeletons: any[] = [];
  if (action.tool === "delete_ai_element") {
    api.updateScene({
      elements: existing.map((e: any) =>
        e.id === action.element_id && e.customData?.createdBy === "ai"
          ? { ...e, isDeleted: true, version: e.version + 1 }
          : e,
      ),
      captureUpdate: CaptureUpdateAction.IMMEDIATELY,
    });
    return created;
  }
  if (action.tool === "point_to" || action.tool === "zoom_to") {
    const target = resolve(action.target);
    if (!target) return created;
    if (action.tool === "point_to") {
      const point = center(target);
      const collaborator = {
        username: "Tutor",
        pointer: {
          ...point,
          tool: "laser",
          renderCursor: true,
          laserColor: "#6965DB",
        },
        button: "up",
        color: { background: "#6965DB", stroke: "#5753C9" },
      };
      api.updateScene({
        collaborators: new Map([["slate-tutor", collaborator]]),
        captureUpdate: CaptureUpdateAction.NEVER,
      });
      onPoint(null);
      setTimeout(
        () =>
          api.updateScene({
            collaborators: new Map(),
            captureUpdate: CaptureUpdateAction.NEVER,
          }),
        2500,
      );
    } else if (followAI) {
      const el = existing.find(
        (e: any) =>
          e.id ===
          ("element_id" in action.target ? action.target.element_id : ""),
      );
      if (el)
        api.scrollToContent([el], {
          animate: !matchMedia("(prefers-reduced-motion: reduce)").matches,
        });
    }
    return created;
  }
  if (action.tool === "write_text") {
    const size = { s: 16, m: 20, l: 28 }[action.size ?? "m"];
    const near = action.near ? resolve(action.near) : null;
    const scene = rects(existing);
    const fallback = {
      x: (scene.length ? Math.max(...scene.map((r) => r.x + r.width)) : 0) + 80,
      y: scene.length ? Math.min(...scene.map((r) => r.y)) : 0,
    };
    const pos = near
      ? freeSpace(
          {
            width: Math.max(100, action.text.length * size * 0.55),
            height: size * 1.4,
          },
          near,
          action.side ?? "right",
          scene,
        )
      : fallback;
    skeletons = [
      {
        type: "text",
        x: pos.x,
        y: pos.y,
        text: action.text,
        fontSize: size,
        fontFamily: 5,
        strokeColor: colors[action.color ?? "ink"],
      },
    ];
  } else if (action.tool === "draw_arrow" || action.tool === "draw_line") {
    const a = resolve(action.start),
      b = resolve(action.end);
    if (!a || !b) return created;
    const [p, q] = clipLine(a, b);
    skeletons = [
      {
        type: action.tool === "draw_arrow" ? "arrow" : "line",
        x: p.x,
        y: p.y,
        points: [
          [0, 0],
          [q.x - p.x, q.y - p.y],
        ],
        strokeColor:
          colors[
            action.color ?? (action.tool === "draw_arrow" ? "violet" : "ink")
          ],
        endArrowhead: action.tool === "draw_arrow" ? "arrow" : null,
      },
      ...(action.label
        ? [
            {
              type: "text",
              x: (p.x + q.x) / 2,
              y: (p.y + q.y) / 2 - 24,
              text: action.label,
              fontSize: 16,
              fontFamily: 5,
              strokeColor: colors[action.color ?? "violet"],
            },
          ]
        : []),
    ];
  } else if ("target" in action) {
    const target = resolve(action.target);
    if (!target) return created;
    const pad = action.padding ?? (action.tool === "draw_circle" ? 10 : 8);
    skeletons = [
      {
        type: action.tool === "draw_circle" ? "ellipse" : "rectangle",
        x: target.x - pad,
        y: target.y - pad,
        width: target.width + pad * 2,
        height: target.height + pad * 2,
        strokeColor:
          action.tool === "highlight"
            ? "transparent"
            : colors[
                action.color ??
                  (action.tool === "draw_circle" ? "red" : "violet")
              ],
        backgroundColor:
          action.tool === "highlight"
            ? colors[action.color ?? "orange"]
            : "transparent",
        fillStyle: "solid",
        opacity: action.tool === "highlight" ? 30 : 100,
        roughness: action.tool === "highlight" ? 0 : 1,
      },
      ...(action.label
        ? [
            {
              type: "text",
              x: target.x,
              y: target.y - pad - 24,
              text: action.label,
              fontSize: 16,
              fontFamily: 5,
              strokeColor: colors[action.color ?? "violet"],
            },
          ]
        : []),
    ];
  }
  const made = tag(convertToExcalidrawElements(skeletons), actionId, step);
  made.forEach((e: any) => created.push(e.id));
  api.updateScene({
    elements: [...existing, ...made],
    captureUpdate: CaptureUpdateAction.IMMEDIATELY,
  });
  return created;
}
export function undoActionGroup(api: any, actionId: string) {
  const existing = api.getSceneElements();
  const matching = existing.filter(
    (e: any) => e.customData?.actionId === actionId && !e.isDeleted,
  );
  const edited = matching.some(
    (e: any) => e.version > (e.customData?.createdVersion ?? e.version),
  );
  if (
    edited &&
    !window.confirm("You edited some of these AI marks. Remove them anyway?")
  )
    return false;
  api.updateScene({
    elements: existing.map((e: any) =>
      e.customData?.actionId === actionId
        ? { ...e, isDeleted: true, version: e.version + 1 }
        : e,
    ),
    captureUpdate: CaptureUpdateAction.IMMEDIATELY,
  });
  return true;
}
