import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Excalidraw, exportToBlob, MainMenu } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";
import {
  Check,
  ChevronLeft,
  Mic,
  Send,
  SlidersHorizontal,
  Square,
  Undo2,
  Volume2,
} from "lucide-react";
import { toast } from "sonner";

import { api as backend } from "@/lib/api";
import { encodeWav } from "@/lib/wav";
import { executeAction, undoActionGroup } from "@/services/actionExecutor";
import { buildCanvasContext } from "@/services/canvasContext";
import type { AIEvent, Mode, Project, Step } from "@/types/api";

type Preferences = {
  mode: Mode;
  language: string;
  speakReplies: boolean;
  followAI: boolean;
};
const defaultPreferences: Preferences = {
  mode: "auto",
  language: "auto",
  speakReplies: true,
  followAI: true,
};
const delay = (ms: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, ms));

function readPreferences(): Preferences {
  try {
    return {
      ...defaultPreferences,
      ...JSON.parse(localStorage.getItem("slate-preferences") ?? "{}"),
    };
  } catch {
    return defaultPreferences;
  }
}

async function dataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

async function makeThumbnail(api: any): Promise<string | undefined> {
  const elements = api
    .getSceneElements()
    .filter((element: any) => !element.isDeleted);
  if (!elements.length) return undefined;
  try {
    return await dataUrl(
      await exportToBlob({
        elements,
        appState: {
          ...api.getAppState(),
          exportBackground: true,
          viewBackgroundColor: "#FFFDF8",
        },
        files: api.getFiles(),
        maxWidthOrHeight: 360,
      }),
    );
  } catch {
    return undefined;
  }
}

export function CanvasPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const initialPrefs = useMemo(readPreferences, []);
  const [project, setProject] = useState<Project | null>(null);
  const [scene, setScene] = useState<any | null>(null);
  const [canvasApi, setCanvasApi] = useState<any>(null);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<Mode>(initialPrefs.mode);
  const [language, setLanguage] = useState(initialPrefs.language);
  const [speakReplies, setSpeakReplies] = useState(initialPrefs.speakReplies);
  const [followAI, setFollowAI] = useState(initialPrefs.followAI);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [status, setStatus] = useState("idle");
  const [caption, setCaption] = useState("");
  const [selected, setSelected] = useState(0);
  const [saveState, setSaveState] = useState("Saved");
  const [actionGroups, setActionGroups] = useState<string[]>([]);
  const [health, setHealth] = useState("");
  const [recording, setRecording] = useState(false);
  const [levels, setLevels] = useState([0.1, 0.1, 0.1, 0.1, 0.1, 0.1]);
  const saveTimer = useRef<number | undefined>(undefined);
  const lastFingerprint = useRef("");
  const sentFiles = useRef(new Set<string>());
  const lastThumbnail = useRef(0);
  const socketRef = useRef<WebSocket | null>(null);
  const requestEpoch = useRef(0);
  const actionId = useRef("");
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const mediaChunks = useRef<Blob[]>([]);
  const actionOcr = useRef<
    Record<string, { text: string; box: [number, number, number, number] }[]>
  >({});
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ttsCache = useRef(
    new Map<string, Promise<{ audio_base64: string; mime: string }>>(),
  );
  const meterCleanup = useRef<(() => void) | null>(null);

  useEffect(() => {
    Promise.all([
      backend.getProject(projectId),
      backend.loadCanvas(projectId),
      backend.health(),
    ])
      .then(([loadedProject, loadedScene, currentHealth]) => {
        setProject(loadedProject);
        setScene(loadedScene);
        sentFiles.current = new Set(Object.keys(loadedScene.files));
        if (!currentHealth.groq_configured || !currentHealth.sarvam_configured)
          setHealth(
            "Add the missing API key to .env and restart the backend. The canvas still works.",
          );
      })
      .catch((error: Error) => {
        toast.error(error.message);
        navigate("/");
      });
  }, [navigate, projectId]);

  useEffect(() => {
    localStorage.setItem(
      "slate-preferences",
      JSON.stringify({ mode, language, speakReplies, followAI }),
    );
  }, [mode, language, speakReplies, followAI]);
  useEffect(
    () => () => {
      socketRef.current?.close();
      meterCleanup.current?.();
      audioRef.current?.pause();
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
    },
    [],
  );

  const saveCanvas = useCallback(
    async (api: any) => {
      const elements = api.getSceneElements();
      const appState = api.getAppState();
      const files = api.getFiles();
      const fingerprint =
        elements
          .map(
            (element: any) =>
              `${element.id}:${element.version}:${element.isDeleted}`,
          )
          .join("|") + Object.keys(files).join("|");
      if (fingerprint === lastFingerprint.current) return;
      lastFingerprint.current = fingerprint;
      setSaveState("Saving…");
      const newlySent: string[] = [];
      const storedFiles = Object.fromEntries(
        Object.entries(files).map(([id, raw]) => {
          const file = raw as Record<string, unknown>;
          const includeData = !sentFiles.current.has(id);
          if (includeData) newlySent.push(id);
          return [
            id,
            { ...file, id, dataURL: includeData ? file.dataURL : undefined },
          ];
        }),
      );
      try {
        const now = Date.now();
        const thumbnail =
          now - lastThumbnail.current >= 10_000
            ? await makeThumbnail(api)
            : undefined;
        await backend.saveCanvas(projectId, {
          elements: elements.filter((element: any) => !element.isDeleted),
          app_state: {
            viewBackgroundColor: appState.viewBackgroundColor,
            scrollX: appState.scrollX,
            scrollY: appState.scrollY,
            zoom: appState.zoom,
          },
          files: storedFiles,
          thumbnail_data_url: thumbnail,
        });
        if (thumbnail) lastThumbnail.current = now;
        newlySent.forEach((id) => sentFiles.current.add(id));
        setSaveState("Saved");
      } catch (error) {
        lastFingerprint.current = "";
        setSaveState("Save failed");
        toast.error((error as Error).message);
      }
    },
    [projectId],
  );

  const onCanvasChange = useCallback(
    (_elements: readonly unknown[], appState: any) => {
      setSelected(Object.keys(appState.selectedElementIds ?? {}).length);
      if (!canvasApi) return;
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(
        () => void saveCanvas(canvasApi),
        1500,
      );
    },
    [canvasApi, saveCanvas],
  );

  const tts = useCallback(
    (text: string) => {
      const key = `${language}:${text}`;
      let pending = ttsCache.current.get(key);
      if (!pending) {
        pending = backend.speak(
          text,
          language === "auto" ? undefined : language,
        );
        ttsCache.current.set(key, pending);
      }
      return pending;
    },
    [language],
  );

  const speak = useCallback(
    async (text: string, epoch: number) => {
      if (!speakReplies) return;
      try {
        const result = await tts(text);
        if (requestEpoch.current !== epoch) return;
        const player = new Audio(
          `data:${result.mime};base64,${result.audio_base64}`,
        );
        audioRef.current = player;
        await player.play();
        await new Promise<void>((resolve) => {
          player.onended = () => resolve();
          player.onerror = () => resolve();
        });
      } catch {
        /* Captions remain visible when TTS is unavailable. */
      }
    },
    [speakReplies, tts],
  );

  const playStep = useCallback(
    async (step: Step, index: number, epoch: number) => {
      if (requestEpoch.current !== epoch || !canvasApi) return;
      setStatus(step.wait_for_student ? "Your turn" : "Drawing…");
      setCaption(step.say ?? step.question ?? "");
      const voice = step.say ? speak(step.say, epoch) : Promise.resolve();
      for (const action of step.actions) {
        if (requestEpoch.current !== epoch) return;
        try {
          await executeAction(
            canvasApi,
            action,
            actionId.current,
            index,
            () => undefined,
            followAI,
            actionOcr.current,
          );
          await delay(350);
        } catch (error) {
          console.warn("Skipped an invalid AI action", error);
        }
      }
      await voice;
      if (step.wait_for_student)
        setCaption(step.question ?? step.say ?? "Your turn");
    },
    [canvasApi, followAI, speak],
  );

  const connect = useCallback(
    () =>
      new Promise<WebSocket>((resolve, reject) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          resolve(socketRef.current);
          return;
        }
        const socket = new WebSocket(
          `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/ai`,
        );
        socket.onopen = () => {
          socketRef.current = socket;
          resolve(socket);
        };
        socket.onerror = () =>
          reject(new Error("Couldn't connect to the AI backend."));
      }),
    [],
  );

  const stop = useCallback(() => {
    requestEpoch.current += 1;
    socketRef.current?.send(JSON.stringify({ type: "cancel" }));
    audioRef.current?.pause();
    audioRef.current = null;
    setStatus("idle");
    setCaption("");
  }, []);

  const ask = useCallback(
    async (override?: string) => {
      const text = (override ?? prompt).trim();
      if (!text || !canvasApi) return;
      const epoch = ++requestEpoch.current;
      setPrompt("");
      setStatus("Reading the canvas…");
      setCaption("");
      actionId.current = crypto.randomUUID();
      try {
        const socket = await connect();
        const payload = await buildCanvasContext(
          canvasApi,
          projectId,
          text,
          mode,
          language,
        );
        actionOcr.current = payload.ocr;
        let queue = Promise.resolve();
        socket.onmessage = (message) => {
          const event = JSON.parse(message.data) as AIEvent;
          if (requestEpoch.current !== epoch) return;
          if (event.type === "status") setStatus(event.message);
          else if (event.type === "warning") console.warn(event.message);
          else if (event.type === "step") {
            if (event.step.say && speakReplies) void tts(event.step.say);
            queue = queue.then(() => playStep(event.step, event.index, epoch));
          } else if (event.type === "done")
            void queue.then(() => {
              if (requestEpoch.current === epoch) {
                setStatus("idle");
                setActionGroups((groups) => [...groups, actionId.current]);
              }
            });
          else if (event.type === "error") {
            setStatus("idle");
            toast.error(event.message);
          }
        };
        socket.send(JSON.stringify({ type: "ask", payload }));
      } catch (error) {
        if (requestEpoch.current === epoch) {
          setStatus("idle");
          toast.error((error as Error).message);
        }
      }
    },
    [
      canvasApi,
      connect,
      language,
      mode,
      playStep,
      projectId,
      prompt,
      speakReplies,
      tts,
    ],
  );

  const startMeter = (stream: MediaStream) => {
    const context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 64;
    const source = context.createMediaStreamSource(stream);
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    let frame = 0;
    const draw = () => {
      analyser.getByteFrequencyData(data);
      setLevels(
        [0, 1, 2, 3, 4, 5].map((_, i) => Math.max(0.08, data[i * 3] / 255)),
      );
      frame = requestAnimationFrame(draw);
    };
    draw();
    meterCleanup.current = () => {
      cancelAnimationFrame(frame);
      source.disconnect();
      void context.close();
    };
  };

  const transcribeRecording = async (stream: MediaStream) => {
    stream.getTracks().forEach((track) => track.stop());
    meterCleanup.current?.();
    setStatus("Transcribing…");
    try {
      const raw = await new Blob(mediaChunks.current).arrayBuffer();
      const context = new AudioContext();
      const decoded = await context.decodeAudioData(raw);
      const offline = new OfflineAudioContext(
        1,
        Math.ceil(decoded.duration * 16000),
        16000,
      );
      const source = offline.createBufferSource();
      source.buffer = decoded;
      source.connect(offline.destination);
      source.start();
      const rendered = await offline.startRendering();
      void context.close();
      const result = await backend.transcribe(
        encodeWav(rendered.getChannelData(0)),
        language === "auto" ? "unknown" : language,
      );
      setPrompt(result.transcript);
      setStatus("idle");
      if (result.transcript) void ask(result.transcript);
    } catch (error) {
      setStatus("idle");
      toast.error((error as Error).message);
    }
  };

  const toggleRecording = async () => {
    if (recording) {
      mediaRecorder.current?.stop();
      setRecording(false);
      return;
    }
    if (status !== "idle") stop();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true },
      });
      mediaChunks.current = [];
      startMeter(stream);
      const recorder = new MediaRecorder(stream);
      mediaRecorder.current = recorder;
      recorder.ondataavailable = (event) =>
        mediaChunks.current.push(event.data);
      recorder.onstop = () => void transcribeRecording(stream);
      recorder.start();
      setRecording(true);
      window.setTimeout(() => {
        if (recorder.state === "recording") {
          recorder.stop();
          setRecording(false);
        }
      }, 28_000);
    } catch {
      toast.error(
        "Microphone access was denied. Allow it or type your request.",
      );
    }
  };

  const rename = async () => {
    if (!project) return;
    const value = window.prompt("Project name", project.title)?.trim();
    if (!value) return;
    try {
      setProject(await backend.renameProject(project.id, value));
    } catch (error) {
      toast.error((error as Error).message);
    }
  };
  const undo = () => {
    const id = actionGroups.at(-1);
    if (!id || !canvasApi) return;
    if (undoActionGroup(canvasApi, id)) {
      setActionGroups((groups) => groups.slice(0, -1));
      toast.success("AI changes removed");
    }
  };

  if (!scene || !project)
    return <div className="error-page">Opening canvas…</div>;
  const uiOptions = {
    canvasActions: {
      loadScene: false,
      saveToActiveFile: false,
      export: false,
      toggleTheme: false,
    },
  } as any;

  return (
    <div className="canvas-page">
      <header className="app-header">
        <div className="header-side">
          <button
            className="button icon ghost"
            aria-label="Back to projects"
            title="Projects"
            onClick={() => navigate("/")}
          >
            <ChevronLeft size={20} />
          </button>
          <button className="project-title" onClick={() => void rename()}>
            {project.title}
          </button>
        </div>
        <div className="header-side">
          <span className="save-state">{saveState}</span>
          {actionGroups.length > 0 && (
            <button className="button" onClick={undo}>
              <Undo2 size={16} />
              <span className="undo-label">Undo AI changes</span>
            </button>
          )}
          <div className="settings-wrap">
            <button
              className="button icon ghost"
              aria-label="Settings"
              title="Settings"
              onClick={() => setSettingsOpen((open) => !open)}
            >
              <SlidersHorizontal size={18} />
            </button>
            {settingsOpen && (
              <div className="settings-menu">
                <label>
                  <span>
                    <Volume2 size={15} />
                    Reply with voice
                  </span>
                  <input
                    type="checkbox"
                    checked={speakReplies}
                    onChange={(event) => setSpeakReplies(event.target.checked)}
                  />
                </label>
                <label>
                  <span>
                    <Check size={15} />
                    Follow AI camera
                  </span>
                  <input
                    type="checkbox"
                    checked={followAI}
                    onChange={(event) => setFollowAI(event.target.checked)}
                  />
                </label>
                <label>
                  <span>Voice language</span>
                  <select
                    value={language}
                    onChange={(event) => setLanguage(event.target.value)}
                  >
                    <option value="auto">Auto</option>
                    <option value="en-IN">English</option>
                    <option value="hi-IN">Hindi</option>
                  </select>
                </label>
              </div>
            )}
          </div>
        </div>
      </header>
      <div className="canvas-wrap">
        {health && <div className="health">{health}</div>}
        <Excalidraw
          excalidrawAPI={setCanvasApi}
          initialData={
            {
              elements: scene.elements,
              appState: {
                ...scene.app_state,
                viewBackgroundColor: "#FFFDF8",
                openSidebar: null,
              },
              files: scene.files,
            } as any
          }
          onChange={onCanvasChange as any}
          theme="light"
          UIOptions={uiOptions}
        >
          <MainMenu>
            <MainMenu.DefaultItems.SaveAsImage />
            <MainMenu.DefaultItems.SearchMenu />
            <MainMenu.DefaultItems.Help />
            <MainMenu.DefaultItems.ClearCanvas />
            <MainMenu.Separator />
            <MainMenu.DefaultItems.ChangeCanvasBackground />
          </MainMenu>
        </Excalidraw>
        {status !== "idle" && <div className="status">{status}</div>}
        <div className="prompt-stack">
          {caption && (
            <div className="caption">
              {caption}
              {status === "Your turn" && (
                <button
                  className="button"
                  onClick={() => void ask("Check my work")}
                >
                  Check my work
                </button>
              )}
            </div>
          )}
          <form
            className="prompt"
            onSubmit={(event) => {
              event.preventDefault();
              void ask();
            }}
          >
            <span className="context-chip">
              {selected ? `${selected} selected` : "Whole canvas"}
            </span>
            {recording ? (
              <div className="level-meter" aria-label="Recording audio">
                {levels.map((level, i) => (
                  <i key={i} style={{ transform: `scaleY(${level})` }} />
                ))}
              </div>
            ) : (
              <input
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="Ask about anything on the canvas"
                aria-label="Ask Slate"
              />
            )}
            <select
              className="button mode"
              value={mode}
              onChange={(event) => setMode(event.target.value as Mode)}
              aria-label="Teaching mode"
            >
              <option value="auto">Auto</option>
              <option value="answer">Answer</option>
              <option value="explain">Explain</option>
              <option value="show_me">Show me</option>
              <option value="solve_with_me">Solve with me</option>
            </select>
            <button
              type="button"
              className={`button icon ${recording ? "danger" : ""}`}
              aria-label={recording ? "Stop recording" : "Speak"}
              title={recording ? "Stop recording" : "Speak"}
              onClick={() => void toggleRecording()}
            >
              <Mic size={18} />
            </button>
            {status !== "idle" && !recording ? (
              <button type="button" className="button primary" onClick={stop}>
                <Square size={15} />
                Stop
              </button>
            ) : (
              <button
                className="button primary icon"
                disabled={!prompt.trim() || recording}
                aria-label="Send"
                title="Send"
              >
                <Send size={17} />
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
