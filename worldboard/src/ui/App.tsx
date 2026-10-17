import { ReactFlowProvider, useReactFlow, useViewport } from "@xyflow/react";
import { CARD_TYPES } from "../core/cardTypes";
import { useWorld } from "../core/store";
import type { CardType } from "../core/types";
import { Canvas } from "./Canvas";
import { CheckIcon, FitIcon, MoonIcon, SunIcon, TypeIcon } from "./icons";
import { useTheme, type ThemeStyle } from "./theme";

const STYLES: { value: ThemeStyle; label: string }[] = [
  { value: "studio", label: "Studio" },
  { value: "sketch", label: "Skizze" },
];

const SAVE_LABEL = { saved: "Gespeichert", saving: "Speichert …", error: "Speichern fehlgeschlagen" };

function Toolbar({ theme }: { theme: ReturnType<typeof useTheme> }) {
  const worldName = useWorld((s) => s.world.boards[0]?.name ?? "Meine Welt");
  const saveStatus = useWorld((s) => s.saveStatus);
  const addCard = useWorld((s) => s.addCard);
  const { screenToFlowPosition } = useReactFlow();

  const addInView = (type: CardType) => {
    const rect = document.querySelector(".canvas")?.getBoundingClientRect();
    if (!rect) return;
    // Leicht versetzt, damit mehrere neue Karten nicht exakt übereinander liegen.
    const jitter = () => (Math.random() - 0.5) * 80;
    const p = screenToFlowPosition({ x: rect.left + rect.width / 2 + jitter(), y: rect.top + rect.height / 2 + jitter() });
    addCard({ type, x: p.x - 130, y: p.y - 60 });
  };

  return (
    <header className="toolbar">
      <div className="toolbar-group brand">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-name">Worldboard</span>
        <span className="brand-world">{worldName}</span>
      </div>

      <nav className="toolbar-group types" aria-label="Neue Karte">
        {CARD_TYPES.map((t) => (
          <button key={t.type} type="button" className="tool-btn" data-type={t.type} onClick={() => addInView(t.type)}>
            <TypeIcon type={t.type} />
            {t.label}
          </button>
        ))}
      </nav>

      <div className="toolbar-right">
        <span className={`save-status is-${saveStatus}`} role="status">
          {saveStatus === "saved" && <CheckIcon size={15} />}
          {SAVE_LABEL[saveStatus]}
        </span>
        <div className="toolbar-group segmented" role="group" aria-label="Stil">
          {STYLES.map((s) => (
            <button
              key={s.value}
              type="button"
              className="tool-btn"
              aria-pressed={theme.style === s.value}
              onClick={() => theme.setStyle(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="tool-btn icon-btn toolbar-group"
          aria-label={theme.mode === "dark" ? "Tagmodus" : "Nachtmodus"}
          title={theme.mode === "dark" ? "Tagmodus" : "Nachtmodus"}
          onClick={() => theme.setMode(theme.mode === "dark" ? "light" : "dark")}
        >
          {theme.mode === "dark" ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>
    </header>
  );
}

function ZoomControl() {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { zoom } = useViewport();
  return (
    <div className="zoom toolbar-group">
      <button type="button" className="tool-btn icon-btn" aria-label="Verkleinern" onClick={() => zoomOut()}>
        −
      </button>
      <span className="zoom-value">{Math.round(zoom * 100)} %</span>
      <button type="button" className="tool-btn icon-btn" aria-label="Vergrößern" onClick={() => zoomIn()}>
        +
      </button>
      <button
        type="button"
        className="tool-btn icon-btn"
        aria-label="Alles zeigen"
        title="Alles zeigen"
        onClick={() => fitView({ maxZoom: 1, padding: 0.2, duration: 200 })}
      >
        <FitIcon />
      </button>
    </div>
  );
}

export function App() {
  const theme = useTheme();
  return (
    <ReactFlowProvider>
      <div className="app">
        <Canvas mode={theme.mode} />
        <Toolbar theme={theme} />
        <p className="hint">Doppelklick: neue Karte · Punkt rechts ziehen: verbinden · Entf: löschen</p>
        <ZoomControl />
      </div>
    </ReactFlowProvider>
  );
}
