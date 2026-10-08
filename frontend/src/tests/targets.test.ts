import { describe, expect, it } from "vitest";
import {
  clipLine,
  freeSpace,
  matchOcr,
  resolveRect,
  similarity,
} from "@/services/targets";

describe("targets", () => {
  it("fuzzy matches OCR and resolves normalized boxes", () => {
    expect(similarity("30°", "30o")).toBe(1);
    expect(
      matchOcr("velocity", [{ text: "velocity", box: [0.2, 0.3, 0.4, 0.5] }]),
    ).toEqual([0.2, 0.3, 0.4, 0.5]);
    expect(
      resolveRect({ element_id: "img", region: [0.25, 0.25, 0.75, 0.75] }, [
        { id: "img", x: 100, y: 50, width: 200, height: 100 },
      ]),
    ).toEqual({ x: 150, y: 75, width: 100, height: 50 });
  });
  it("places new work without overlap", () => {
    const result = freeSpace(
      { width: 50, height: 30 },
      { x: 0, y: 0, width: 100, height: 100 },
      "right",
      [{ x: 128, y: 0, width: 50, height: 30 }],
    );
    expect(result.y).toBeGreaterThanOrEqual(128);
  });
  it("clips arrows to element edges", () => {
    const [start, end] = clipLine(
      { x: 0, y: 0, width: 100, height: 100 },
      { x: 200, y: 0, width: 100, height: 100 },
      0,
    );
    expect(start).toEqual({ x: 100, y: 50 });
    expect(end).toEqual({ x: 200, y: 50 });
  });
});
