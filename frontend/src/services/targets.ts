import type { Target } from "@/types/api";

export type Rect = { x: number; y: number; width: number; height: number };
export type OcrWord = { text: string; box: [number, number, number, number] };
const normalized = (value: string) =>
  value
    .toLowerCase()
    .replace(/[°º]/g, "o")
    .replace(/[01li]/g, (c) => (c === "0" || c === "o" ? "o" : "i"))
    .replace(/[^a-z0-9]/g, "");
export function similarity(a: string, b: string): number {
  a = normalized(a);
  b = normalized(b);
  if (!a || !b) return 0;
  const row = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let prev = row[0];
    row[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const old = row[j];
      row[j] = Math.min(
        row[j] + 1,
        row[j - 1] + 1,
        prev + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
      prev = old;
    }
  }
  return 1 - row[b.length] / Math.max(a.length, b.length);
}
export function matchOcr(
  text: string,
  words: OcrWord[],
): [number, number, number, number] | null {
  let best = 0,
    box: null | [number, number, number, number] = null;
  for (let i = 0; i < words.length; i++)
    for (let n = 1; n <= Math.min(5, words.length - i); n++) {
      const slice = words.slice(i, i + n);
      const score = similarity(text, slice.map((w) => w.text).join(" "));
      if (score > best) {
        best = score;
        box = [
          Math.min(...slice.map((w) => w.box[0])),
          Math.min(...slice.map((w) => w.box[1])),
          Math.max(...slice.map((w) => w.box[2])),
          Math.max(...slice.map((w) => w.box[3])),
        ];
      }
    }
  return best >= 0.7 ? box : null;
}
export function resolveRect(
  target: Target,
  elements: readonly Record<string, unknown>[],
  ocr: Record<string, OcrWord[]> = {},
): Rect | null {
  if ("x" in target) return { x: target.x, y: target.y, width: 0, height: 0 };
  const el = elements.find((item) => item.id === target.element_id) as
    Record<string, unknown> | undefined;
  if (!el) return null;
  const base = {
    x: Number(el.x),
    y: Number(el.y),
    width: Number(el.width),
    height: Number(el.height),
  };
  let region = target.text
    ? matchOcr(target.text, ocr[target.element_id] ?? [])
    : null;
  region ??= target.region ?? null;
  return region
    ? {
        x: base.x + region[0] * base.width,
        y: base.y + region[1] * base.height,
        width: (region[2] - region[0]) * base.width,
        height: (region[3] - region[1]) * base.height,
      }
    : base;
}
export const center = (r: Rect) => ({
  x: r.x + r.width / 2,
  y: r.y + r.height / 2,
});
export function clipLine(
  start: Rect,
  end: Rect,
  gap = 6,
): [{ x: number; y: number }, { x: number; y: number }] {
  const a = center(start),
    b = center(end),
    dx = b.x - a.x,
    dy = b.y - a.y,
    length = Math.hypot(dx, dy) || 1,
    ux = dx / length,
    uy = dy / length;
  const edge = (
    rect: Rect,
    from: { x: number; y: number },
    vx: number,
    vy: number,
  ) => {
    if (!rect.width && !rect.height) return from;
    const tx = vx === 0 ? Infinity : rect.width / 2 / Math.abs(vx);
    const ty = vy === 0 ? Infinity : rect.height / 2 / Math.abs(vy);
    const t = Math.min(tx, ty);
    return { x: from.x + vx * t, y: from.y + vy * t };
  };
  const p = edge(start, a, ux, uy),
    q = edge(end, b, -ux, -uy);
  return [
    { x: p.x + ux * gap, y: p.y + uy * gap },
    { x: q.x - ux * gap, y: q.y - uy * gap },
  ];
}
export function freeSpace(
  size: { width: number; height: number },
  near: Rect,
  side: string,
  occupied: Rect[],
): { x: number; y: number } {
  const gap = 28;
  const options: Record<string, { x: number; y: number }> = {
    right: { x: near.x + near.width + gap, y: near.y },
    left: { x: near.x - size.width - gap, y: near.y },
    above: { x: near.x, y: near.y - size.height - gap },
    below: { x: near.x, y: near.y + near.height + gap },
  };
  for (const name of [side, "right", "below", "left", "above"]) {
    const p = options[name];
    if (
      p &&
      !occupied.some(
        (r) =>
          p.x < r.x + r.width + 12 &&
          p.x + size.width + 12 > r.x &&
          p.y < r.y + r.height + 12 &&
          p.y + size.height + 12 > r.y,
      )
    )
      return p;
  }
  return options.right;
}
