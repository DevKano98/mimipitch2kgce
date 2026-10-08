import { createWorker, OEM } from "tesseract.js";
import type { OcrWord } from "@/services/targets";

const cache = new Map<string, Promise<OcrWord[]>>();
let workerPromise: ReturnType<typeof createWorker> | null = null;
const worker = () => (workerPromise ??= createWorker("eng", OEM.LSTM_ONLY));
export function indexImage(
  fileId: string,
  dataUrl: string,
): Promise<OcrWord[]> {
  const existing = cache.get(fileId);
  if (existing) return existing;
  const job = (async () => {
    const instance = await worker();
    const result: any = await instance.recognize(dataUrl, {}, { blocks: true });
    const blocks = result.data.blocks ?? [];
    const words: any[] = blocks.flatMap((block: any) =>
      (block.paragraphs ?? []).flatMap((paragraph: any) =>
        (paragraph.lines ?? []).flatMap((line: any) => line.words ?? []),
      ),
    );
    const width =
      result.data.imageWidth ??
      Math.max(1, ...words.map((w) => w.bbox?.x1 ?? 1));
    const height =
      result.data.imageHeight ??
      Math.max(1, ...words.map((w) => w.bbox?.y1 ?? 1));
    return words
      .filter((w) => w.text?.trim())
      .map((w) => ({
        text: w.text.trim(),
        box: [
          w.bbox.x0 / width,
          w.bbox.y0 / height,
          w.bbox.x1 / width,
          w.bbox.y1 / height,
        ] as [number, number, number, number],
      }));
  })();
  cache.set(fileId, job);
  return job;
}

export async function ocrForElements(
  elements: readonly any[],
  files: Record<string, any>,
  timeoutMs = 6000,
): Promise<Record<string, OcrWord[]>> {
  const entries = elements
    .filter((e) => e.type === "image" && e.fileId && files[e.fileId]?.dataURL)
    .map(
      async (e) =>
        [e.id, await indexImage(e.fileId, files[e.fileId].dataURL)] as const,
    );
  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error("OCR timeout")), timeoutMs),
  );
  try {
    return Object.fromEntries(
      await Promise.race([Promise.all(entries), timeout]),
    );
  } catch {
    return {};
  }
}
