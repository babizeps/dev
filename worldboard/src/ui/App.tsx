import { ReactFlowProvider, useReactFlow, useViewport } from "@xyflow/react";
import { useEffect, useRef, useState } from "react";
import { CARD_TYPES } from "../core/cardTypes";
import { useWorld } from "../core/store";
import type { CardType } from "../core/types";
import { useStorage } from "./assets";
import { Canvas } from "./Canvas";
import { CardMenus } from "./CardMenus";
import { AutoIcon, MoonIcon, RedoIcon, SunIcon, TypeIcon, UndoIcon } from "./icons";
import { useTheme, type ModeSetting, type ThemeStyle } from "./theme";

const STYLES: { value: ThemeStyle; label: string }[] = [
  { value: "studio", label: "Studio" },
  { value: "sketch", label: "Skizzenbuch" },
];

const MODES: { value: ModeSetting; label: string; name: string }[] = [
  { value: "light", label: "Hell", name: "Tagmodus" },
  { value: "dark", label: "Dunkel", name: "Nachtmodus" },
  { value: "auto", label: "Auto", name: "Automatisch wie das System" },
];

const SAVE_LABEL = { saved: "Gespeichert", saving: "Speichert …", error: "Speichern fehlgeschlagen" };

const DEFAULT_WORLD_NAME = "Meine Welt";

/** Oben links: Name der App und der Welt. Der Weltname lässt sich direkt überschreiben. */
function TitleIsland() {
  const worldName = useWorld((s) => s.world.boards[0]?.name ?? DEFAULT_WORLD_NAME);
  const renameWorld = useWorld((s) => s.renameWorld);
  return (
    <div className="island title-island">
      <span className="brand-name">Worldboard</span>
      {/* Das unsichtbare Spiegelbild im ::after gibt dem Feld genau die Breite seines Textes. */}
      <span className="world-name" data-value={worldName || DEFAULT_WORLD_NAME}>
        <input
          className="world-name-input"
          size={1}
          value={worldName}
          placeholder={DEFAULT_WORLD_NAME}
          aria-label="Name der Welt"
          spellCheck={false}
          onChange={(e) => renameWorld(e.target.value)}
          onBlur={() => !worldName.trim() && renameWorld(DEFAULT_WORLD_NAME)}
          onKeyDown={(e) => (e.key === "Enter" || e.key === "Escape") && e.currentTarget.blur()}
        />
      </span>
    </div>
  );
}

/** Oben rechts: Speicherstatus und das Ansicht-Menü (Stil und Modus). */
function StatusIsland({ theme }: { theme: ReturnType<typeof useTheme> }) {
  const saveStatus = useWorld((s) => s.saveStatus);
  const { location } = useStorage();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown, true);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="island status-island" ref={ref}>
      {/* Nur der Punkt ist sichtbar; der Text bleibt für Screenreader und steht im Tooltip. */}
      <span className={`save-status is-${saveStatus}`} role="status" title={`${SAVE_LABEL[saveStatus]} · ${location}`}>
        <span className="save-dot" aria-hidden="true" />
        <span className="save-label">{SAVE_LABEL[saveStatus]}</span>
      </span>
      <button
        type="button"
        className="island-btn"
        aria-label="Ansicht"
        title="Ansicht"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {theme.mode === "dark" ? <MoonIcon /> : <SunIcon />}
      </button>
      {open && (
        <div className="view-menu" role="dialog" aria-label="Ansicht">
          <div className="view-menu-label">Stil</div>
          <div className="style-tiles" role="group" aria-label="Stil">
            {STYLES.map((s) => (
              <button
                key={s.value}
                type="button"
                className="style-tile"
                aria-pressed={theme.style === s.value}
                onClick={() => theme.setStyle(s.value)}
              >
                {/* Kleine Vorschau einer Karte im jeweiligen Stil */}
                <span className={`style-preview is-${s.value}`} aria-hidden="true">
                  <span className="style-preview-card">{s.value === "sketch" ? "Mira" : ""}</span>
                </span>
                {s.label}
              </button>
            ))}
          </div>
          <div className="view-menu-separator" />
          <div className="view-menu-label">Erscheinungsbild</div>
          <div className="mode-tiles" role="group" aria-label="Erscheinungsbild">
            {MODES.map((m) => (
              <button
                key={m.value}
                type="button"
                className="mode-tile"
                aria-label={m.name}
                title={m.name}
                aria-pressed={theme.modeSetting === m.value}
                onClick={() => theme.setModeSetting(m.value)}
              >
                {m.value === "dark" ? <MoonIcon size={19} /> : m.value === "auto" ? <AutoIcon size={19} /> : <SunIcon size={19} />}
                {m.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** So nah am unteren Rand muss die Maus kommen, damit das Dock erscheint. */
const DOCK_REVEAL_PX = 120;
const DOCK_HIDE_DELAY_MS = 500;

/**
 * Blendet das Dock ein, solange die Maus unten im Fenster ist oder ein Knopf darin den Fokus hat.
 * Bei einer leeren Welt bleibt es sichtbar, damit der Einstieg auffindbar ist.
 */
function useDockVisible(dock: React.RefObject<HTMLDivElement | null>) {
  const hasCards = useWorld((s) => s.world.cards.some((c) => c.deletedAt === null));
  const [near, setNear] = useState(false);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    let hideTimer: ReturnType<typeof setTimeout> | undefined;
    const onMove = (e: PointerEvent) => {
      const inZone = e.clientY >= window.innerHeight - DOCK_REVEAL_PX || !!dock.current?.contains(e.target as Node);
      if (inZone) {
        clearTimeout(hideTimer);
        hideTimer = undefined;
        setNear(true);
      } else if (!hideTimer) {
        hideTimer = setTimeout(() => {
          hideTimer = undefined;
          setNear(false);
        }, DOCK_HIDE_DELAY_MS);
      }
    };
    const onLeave = () => setNear(false);
    window.addEventListener("pointermove", onMove);
    document.documentElement.addEventListener("pointerleave", onLeave);
    return () => {
      clearTimeout(hideTimer);
      window.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("pointerleave", onLeave);
    };
  }, [dock]);

  return { visible: near || focused || !hasCards, setFocused };
}

/** Unten in der Mitte: neue Karten (mit Namen) sowie Rückgängig und Wiederholen. */
function Dock() {
  const ref = useRef<HTMLDivElement>(null);
  const { visible, setFocused } = useDockVisible(ref);
  const addCard = useWorld((s) => s.addCard);
  const canUndo = useWorld((s) => s.past.length > 0);
  const canRedo = useWorld((s) => s.future.length > 0);
  const { undo, redo } = useWorld.getState();
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
    <div
      ref={ref}
      className={`dock${visible ? "" : " is-hidden"}`}
      onFocus={() => setFocused(true)}
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget as Node) && setFocused(false)}
    >
      <nav className="dock-group" aria-label="Neue Karte">
        {CARD_TYPES.map((t) => (
          <button
            key={t.type}
            type="button"
            className="dock-btn"
            data-type={t.type}
            title={`Neue Karte: ${t.label}`}
            onClick={() => addInView(t.type)}
          >
            <TypeIcon type={t.type} size={20} />
            <span>{t.label}</span>
          </button>
        ))}
      </nav>
      <span className="dock-separator" aria-hidden="true" />
      <div className="dock-group">
        <button type="button" className="dock-btn is-icon" aria-label="Rückgängig" title="Rückgängig (Strg+Z)" disabled={!canUndo} onClick={undo}>
          <UndoIcon size={18} />
        </button>
        <button type="button" className="dock-btn is-icon" aria-label="Wiederholen" title="Wiederholen (Strg+Umschalt+Z)" disabled={!canRedo} onClick={redo}>
          <RedoIcon size={18} />
        </button>
      </div>
    </div>
  );
}

/**
 * Zoom: bei 100 % unsichtbar. Nach dem Zoomen erscheint nur die Prozentzahl;
 * ein Klick passt alles ein, ein weiterer Klick geht zurück auf 100 %.
 */
function ZoomControl() {
  const { fitView, zoomTo, getZoom } = useReactFlow();
  const { zoom } = useViewport();
  const [fittedZoom, setFittedZoom] = useState<number | null>(null);
  const percent = Math.round(zoom * 100);
  const hidden = percent === 100;
  const fitted = fittedZoom !== null && Math.abs(zoom - fittedZoom) < 0.001;
  const label = fitted ? "Zurück auf 100 %" : "Alles einpassen";

  const toggle = async () => {
    if (fitted) {
      setFittedZoom(null);
      await zoomTo(1, { duration: 200 });
    } else {
      await fitView({ maxZoom: 1, padding: 0.2, duration: 200 });
      setFittedZoom(getZoom());
    }
  };

  return (
    <div className={`island zoom${hidden ? " is-hidden" : ""}`} aria-hidden={hidden || undefined}>
      <button type="button" className="zoom-btn" aria-label={`${percent} %, ${label}`} title={label} tabIndex={hidden ? -1 : undefined} onClick={toggle}>
        {percent} %
      </button>
    </div>
  );
}

/** Strg/Cmd+Z, Strg/Cmd+Umschalt+Z und Strg+Y – überall, auch beim Tippen in einer Karte. */
function useUndoShortcuts() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
      const key = e.key.toLowerCase();
      const isUndo = key === "z" && !e.shiftKey;
      const isRedo = (key === "z" && e.shiftKey) || key === "y";
      if (!isUndo && !isRedo) return;
      e.preventDefault();
      const { undo, redo, past, future } = useWorld.getState();
      // Verschwindet die Karte, in der der Cursor steht, verschluckt der Browser das Loslassen
      // der Taste – React Flow hielte sie dann für gedrückt und Entf ginge nicht mehr.
      const target = isUndo ? past[past.length - 1] : future[future.length - 1];
      const active = document.activeElement as HTMLElement | null;
      const cardId = active?.closest<HTMLElement>(".react-flow__node")?.dataset.id;
      if (target && cardId && !target.cards.some((c) => c.id === cardId && c.deletedAt === null)) active?.blur();
      if (isUndo) undo();
      else redo();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

export function App() {
  const theme = useTheme();
  useUndoShortcuts();
  return (
    <ReactFlowProvider>
      <div className="app">
        <Canvas mode={theme.mode} />
        <TitleIsland />
        <StatusIsland theme={theme} />
        <Dock />
        <ZoomControl />
        <CardMenus />
      </div>
    </ReactFlowProvider>
  );
}
