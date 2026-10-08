import { exportToBlob } from "@excalidraw/excalidraw";
import { ocrForElements } from "@/services/ocr";

const blobDataUrl = (blob: Blob) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
export async function buildCanvasContext(
  api: any,
  projectId: string,
  prompt: string,
  mode: string,
  language: string,
) {
  const elements = api.getSceneElements().filter((e: any) => !e.isDeleted);
  const appState = api.getAppState();
  const files = api.getFiles();
  const selectedIds = Object.keys(appState.selectedElementIds ?? {});
  const selected = elements.filter((e: any) => selectedIds.includes(e.id));
  const exportElements = selected.length ? selected : elements;
  const images: any[] = [];
  if (exportElements.length) {
    try {
      const blob = await exportToBlob({
        elements: exportElements,
        appState: {
          ...appState,
          exportBackground: true,
          viewBackgroundColor: "#FFFDF8",
        },
        files,
        maxWidthOrHeight: 1500,
      });
      images.push({
        label: selected.length ? "Selected canvas content" : "Canvas overview",
        data_url: await blobDataUrl(blob),
        element_ids: exportElements.map((e: any) => e.id),
      });
    } catch {
      /* text-only context still works */
    }
  }
  return {
    project_id: projectId,
    prompt,
    mode,
    language: language === "auto" ? null : language,
    selected_ids: selectedIds,
    elements: elements
      .slice(-400)
      .map((e: any) => ({
        id: e.id,
        type: e.type,
        x: e.x,
        y: e.y,
        width: e.width,
        height: e.height,
        text: e.text?.slice(0, 120),
        created_by: e.customData?.createdBy === "ai" ? "ai" : "user",
      })),
    viewport: {
      x: appState.scrollX ?? 0,
      y: appState.scrollY ?? 0,
      width: window.innerWidth,
      height: window.innerHeight - 48,
      zoom: appState.zoom?.value ?? 1,
    },
    images,
    ocr: await ocrForElements(exportElements, files),
  };
}
