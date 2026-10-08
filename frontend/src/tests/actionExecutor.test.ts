import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@excalidraw/excalidraw", () => ({
  CaptureUpdateAction: { IMMEDIATELY: "IMMEDIATELY", NEVER: "NEVER" },
  convertToExcalidrawElements: (items: any[]) =>
    items.map((item, index) => ({
      ...item,
      id: `made-${index}`,
      version: 1,
      isDeleted: false,
    })),
}));
import { executeAction, undoActionGroup } from "@/services/actionExecutor";

describe("action executor", () => {
  let scene: any[];
  let api: any;
  let updates: any[];
  beforeEach(() => {
    scene = [
      {
        id: "student",
        type: "rectangle",
        x: 0,
        y: 0,
        width: 100,
        height: 100,
        version: 1,
        isDeleted: false,
      },
      {
        id: "other",
        type: "rectangle",
        x: 200,
        y: 0,
        width: 100,
        height: 100,
        version: 1,
        isDeleted: false,
      },
    ];
    updates = [];
    api = {
      getSceneElements: () => scene,
      updateScene: (update: any) => {
        updates.push(update);
        if (update.elements) scene = update.elements;
      },
      scrollToContent: vi.fn(),
    };
    vi.stubGlobal("matchMedia", () => ({ matches: false }));
  });
  it("tags every created element", async () => {
    const ids = await executeAction(
      api,
      { tool: "write_text", text: "Hint", near: { element_id: "student" } },
      "action",
      2,
      vi.fn(),
    );
    expect(ids).toEqual(["made-0"]);
    expect(scene.at(-1).customData).toMatchObject({
      createdBy: "ai",
      actionId: "action",
      step: 2,
    });
  });
  it("never deletes student work", async () => {
    await executeAction(
      api,
      { tool: "delete_ai_element", element_id: "student" },
      "action",
      0,
      vi.fn(),
    );
    expect(scene[0].isDeleted).toBe(false);
  });
  it("undoes exactly one action group", () => {
    scene.push(
      {
        id: "ai-a",
        version: 1,
        isDeleted: false,
        customData: { createdBy: "ai", actionId: "a", createdVersion: 1 },
      },
      {
        id: "ai-b",
        version: 1,
        isDeleted: false,
        customData: { createdBy: "ai", actionId: "b", createdVersion: 1 },
      },
    );
    expect(undoActionGroup(api, "a")).toBe(true);
    expect(scene.find((item) => item.id === "ai-a").isDeleted).toBe(true);
    expect(scene.find((item) => item.id === "ai-b").isDeleted).toBe(false);
  });
  it("uses OCR boxes for text targets", async () => {
    await executeAction(
      api,
      { tool: "highlight", target: { element_id: "student", text: "30°" } },
      "action",
      0,
      vi.fn(),
      true,
      { student: [{ text: "30o", box: [0.2, 0.3, 0.4, 0.5] }] },
    );
    expect(scene.at(-1)).toMatchObject({ x: 12, y: 22, width: 36, height: 36 });
  });
  it.each([
    [
      {
        tool: "draw_arrow",
        start: { element_id: "student" },
        end: { element_id: "other" },
      },
      "arrow",
    ],
    [
      {
        tool: "draw_line",
        start: { element_id: "student" },
        end: { element_id: "other" },
      },
      "line",
    ],
    [
      { tool: "draw_rectangle", target: { element_id: "student" } },
      "rectangle",
    ],
    [{ tool: "draw_circle", target: { element_id: "student" } }, "ellipse"],
  ] as const)("converts %s to an Excalidraw %s", async (action, type) => {
    await executeAction(api, action as any, "action", 0, vi.fn());
    expect(scene.at(-1).type).toBe(type);
  });
  it("uses an ephemeral collaborator for pointing", async () => {
    vi.useFakeTimers();
    await executeAction(
      api,
      { tool: "point_to", target: { element_id: "student" } },
      "action",
      0,
      vi.fn(),
    );
    expect(updates.at(-1).collaborators.size).toBe(1);
    vi.runAllTimers();
    expect(updates.at(-1).collaborators.size).toBe(0);
    vi.useRealTimers();
  });
  it("follows the target only when camera follow is enabled", async () => {
    await executeAction(
      api,
      { tool: "zoom_to", target: { element_id: "student" } },
      "action",
      0,
      vi.fn(),
      true,
    );
    expect(api.scrollToContent).toHaveBeenCalledOnce();
    api.scrollToContent.mockClear();
    await executeAction(
      api,
      { tool: "zoom_to", target: { element_id: "student" } },
      "action",
      0,
      vi.fn(),
      false,
    );
    expect(api.scrollToContent).not.toHaveBeenCalled();
  });
});
