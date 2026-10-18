import { beforeEach, describe, expect, it, vi } from "vitest";
import { emptyWorld } from "./migrations";
import { useWorld } from "./store";
import { liveCards, liveEdges } from "./world";

const state = () => useWorld.getState();
const titles = () => liveCards(state().world).map((c) => c.title);

beforeEach(() => {
  vi.useRealTimers();
  state().setWorld(emptyWorld(0));
});

describe("Rückgängig und Wiederholen", () => {
  it("macht das Anlegen einer Karte rückgängig und wiederholt es", () => {
    state().addCard({ type: "figur", x: 0, y: 0, title: "Mira" });
    expect(titles()).toEqual(["Mira"]);
    state().undo();
    expect(titles()).toEqual([]);
    state().redo();
    expect(titles()).toEqual(["Mira"]);
  });

  it("bündelt schnelles Tippen im selben Feld zu einem Schritt", () => {
    vi.useFakeTimers();
    const id = state().addCard({ type: "notiz", x: 0, y: 0 });
    for (const t of ["M", "Mi", "Mir", "Mira"]) {
      state().updateCard(id, { title: t });
      vi.advanceTimersByTime(200);
    }
    vi.advanceTimersByTime(1500);
    state().updateCard(id, { title: "Mira V" });
    state().undo();
    expect(titles()).toEqual(["Mira"]);
    state().undo();
    expect(titles()).toEqual([""]);
  });

  it("trennt Typwechsel vom Tippen", () => {
    const id = state().addCard({ type: "notiz", x: 0, y: 0 });
    state().updateCard(id, { title: "Hafen" });
    state().updateCard(id, { type: "ort" });
    state().undo();
    expect(liveCards(state().world)[0]).toMatchObject({ type: "notiz", title: "Hafen" });
  });

  it("holt gelöschte Karten samt Verbindung zurück", () => {
    const a = state().addCard({ type: "figur", x: 0, y: 0 });
    const b = state().addCard({ type: "ort", x: 0, y: 0 });
    state().connect(a, b);
    state().remove([a], []);
    expect(liveEdges(state().world)).toHaveLength(0);
    state().undo();
    expect(liveCards(state().world)).toHaveLength(2);
    expect(liveEdges(state().world)).toHaveLength(1);
  });

  it("verwirft Wiederholen nach einer neuen Änderung", () => {
    state().addCard({ type: "figur", x: 0, y: 0, title: "A" });
    state().undo();
    state().addCard({ type: "figur", x: 0, y: 0, title: "B" });
    state().redo();
    expect(titles()).toEqual(["B"]);
    expect(state().future).toHaveLength(0);
  });

  it("verschiebt mehrere Karten als einen Schritt", () => {
    const a = state().addCard({ type: "figur", x: 0, y: 0 });
    const b = state().addCard({ type: "ort", x: 0, y: 0 });
    state().moveCards([{ id: a, x: 10, y: 10 }, { id: b, x: 20, y: 20 }]);
    state().undo();
    expect(liveCards(state().world).map((c) => c.x)).toEqual([0, 0]);
  });

  it("ignoriert Rückgängig ohne Verlauf und setWorld leert ihn", () => {
    state().undo();
    state().addCard({ type: "figur", x: 0, y: 0 });
    state().setWorld(emptyWorld(0));
    expect(state().past).toHaveLength(0);
    state().undo();
    expect(titles()).toEqual([]);
  });
});

describe("Weltname", () => {
  it("benennt um und lässt sich rückgängig machen", () => {
    state().renameWorld("Glasküste");
    expect(state().world.boards[0].name).toBe("Glasküste");
    state().undo();
    expect(state().world.boards[0].name).toBe("Meine Welt");
  });
});
