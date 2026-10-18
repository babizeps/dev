import { describe, expect, it } from "vitest";
import { emptyWorld } from "./migrations";
import { addCard, connect, duplicateCard, liveCards, liveEdges, moveCards, removeCards, removeEdges, restore, updateCard } from "./world";

const base = () => {
  let w = emptyWorld(0);
  w = addCard(w, { type: "figur", x: 0, y: 0, title: "Mira" }, 1, "a");
  w = addCard(w, { type: "ort", x: 100, y: 0, title: "Hafen" }, 1, "b");
  return w;
};

describe("Karten", () => {
  it("legt eine Karte mit ID, Zeitstempel und Standardwerten an", () => {
    const [card] = liveCards(addCard(emptyWorld(0), { type: "notiz", x: 5, y: 6 }, 42, "x"));
    expect(card).toMatchObject({ id: "x", boardId: "root", type: "notiz", x: 5, y: 6, width: null, title: "", text: "", image: null, fields: {}, updatedAt: 42, deletedAt: null });
  });

  it("setzt updatedAt bei Änderungen", () => {
    const w = updateCard(base(), "a", { title: "Mira Vell", x: 10 }, 99);
    expect(w.cards[0]).toMatchObject({ title: "Mira Vell", x: 10, updatedAt: 99 });
    expect(w.cards[1].updatedAt).toBe(1);
  });

  it("lässt die Welt unverändert, wenn sich nichts ändert", () => {
    const w = base();
    expect(updateCard(w, "a", { title: "Mira" }, 99)).toBe(w);
    expect(updateCard(w, "fehlt", { title: "x" }, 99)).toBe(w);
  });

  it("löscht nur per Vermerk und nimmt die Verbindungen mit", () => {
    let w = connect(base(), "a", "b", 2, "e1");
    w = removeCards(w, ["a"], 5);
    expect(w.cards.find((c) => c.id === "a")).toMatchObject({ deletedAt: 5, updatedAt: 5 });
    expect(w.edges[0]).toMatchObject({ deletedAt: 5, updatedAt: 5 });
    expect(liveCards(w).map((c) => c.id)).toEqual(["b"]);
    expect(liveEdges(w)).toEqual([]);
  });

  it("ändert gelöschte Karten nicht mehr", () => {
    const w = removeCards(base(), ["a"], 5);
    expect(updateCard(w, "a", { title: "neu" }, 9)).toBe(w);
  });
});

describe("Verbindungen", () => {
  it("verbindet zwei Karten", () => {
    const w = connect(base(), "a", "b", 2, "e1");
    expect(liveEdges(w)).toEqual([{ id: "e1", boardId: "root", from: "a", to: "b", label: "", updatedAt: 2, deletedAt: null }]);
  });

  it("verhindert Selbstverbindungen, Doppelte und Verbindungen zu fehlenden Karten", () => {
    const w = connect(base(), "a", "b", 2, "e1");
    expect(connect(w, "a", "a", 3)).toBe(w);
    expect(connect(w, "a", "b", 3)).toBe(w);
    expect(connect(w, "b", "a", 3)).toBe(w);
    expect(connect(w, "a", "fehlt", 3)).toBe(w);
  });

  it("löscht eine Verbindung per Vermerk und erlaubt sie danach neu", () => {
    let w = removeEdges(connect(base(), "a", "b", 2, "e1"), ["e1"], 4);
    expect(w.edges[0].deletedAt).toBe(4);
    w = connect(w, "a", "b", 5, "e2");
    expect(liveEdges(w).map((e) => e.id)).toEqual(["e2"]);
  });
});

describe("restore (Rückgängig)", () => {
  it("stellt einen früheren Stand her und setzt nur geänderte Zeitstempel neu", () => {
    const before = base();
    const after = updateCard(before, "a", { title: "Mira Vell" }, 5);
    const undone = restore(after, before, 9);
    expect(liveCards(undone).map((c) => c.title)).toEqual(["Mira", "Hafen"]);
    expect(undone.cards.find((c) => c.id === "a")?.updatedAt).toBe(9);
    expect(undone.cards.find((c) => c.id === "b")).toBe(before.cards[1]);
  });

  it("markiert eine rückgängig gemachte neue Karte als gelöscht statt sie zu entfernen", () => {
    const before = base();
    const after = connect(addCard(before, { type: "ort", x: 0, y: 0 }, 5, "c"), "a", "c", 5, "e1");
    const undone = restore(after, before, 9);
    expect(undone.cards.find((c) => c.id === "c")).toMatchObject({ deletedAt: 9, updatedAt: 9 });
    expect(undone.edges.find((e) => e.id === "e1")).toMatchObject({ deletedAt: 9, updatedAt: 9 });
    expect(liveCards(undone).map((c) => c.id)).toEqual(["a", "b"]);
  });

  it("holt eine gelöschte Karte samt Verbindung zurück", () => {
    const before = connect(base(), "a", "b", 2, "e1");
    const after = removeCards(before, ["a"], 5);
    const undone = restore(after, before, 9);
    expect(undone.cards.find((c) => c.id === "a")).toMatchObject({ deletedAt: null, updatedAt: 9 });
    expect(liveEdges(undone).map((e) => e.id)).toEqual(["e1"]);
  });
});

describe("moveCards", () => {
  it("verschiebt mehrere Karten in einem Schritt", () => {
    const w = moveCards(base(), [{ id: "a", x: 10, y: 20 }, { id: "b", x: 30, y: 40 }], 7);
    expect(w.cards.map((c) => [c.x, c.y, c.updatedAt])).toEqual([[10, 20, 7], [30, 40, 7]]);
  });
});

describe("duplicateCard", () => {
  it("kopiert Inhalt und Breite versetzt, aber nicht die Verbindungen", () => {
    let w = updateCard(connect(base(), "a", "b", 2, "e1"), "a", { text: "Schmugglerin", width: 320 }, 3);
    w = duplicateCard(w, "a", 9, "a2");
    expect(w.cards.find((c) => c.id === "a2")).toMatchObject({ title: "Mira", text: "Schmugglerin", width: 320, x: 32, y: 32, updatedAt: 9, deletedAt: null });
    expect(liveEdges(w).map((e) => e.id)).toEqual(["e1"]);
  });

  it("ignoriert gelöschte oder fehlende Karten", () => {
    const w = removeCards(base(), ["a"], 5);
    expect(duplicateCard(w, "a", 9)).toBe(w);
    expect(duplicateCard(w, "fehlt", 9)).toBe(w);
  });
});
