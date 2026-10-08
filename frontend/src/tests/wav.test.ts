import { describe, expect, it } from "vitest";
import { encodeWav } from "@/lib/wav";

describe("wav encoder", () => {
  it("writes a PCM WAV header", async () => {
    const blob = encodeWav(new Float32Array([0, 1, -1]), 16000);
    const buffer = await new Promise<ArrayBuffer>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as ArrayBuffer);
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(blob);
    });
    const bytes = new Uint8Array(buffer);
    expect(new TextDecoder().decode(bytes.slice(0, 4))).toBe("RIFF");
    expect(blob.size).toBe(50);
  });
});
