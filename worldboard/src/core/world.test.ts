import { describe, expect, it } from "vitest";
import { emptyWorld } from "./migrations";
import { addCard, connect, liveCards, liveEdges, removeCards, removeEdges, updateCard } from "./world";

const base = () => {
  let w = emptyWorld(0);
  w = addCard(w, { type: "figur", x: 0, y: 0, title: "Mira" }, 1, "a");
  w = addCard(w, { type: "ort", x: 100, y: 0, title: "Hafen" }, 1, "b");
  return w;
};

describe("Karten", () => {
  it("legt eine Karte mit ID, Zeitstempel und Standardwerten an", () => {
    const [card] = liveCards(addCard(emptyWorld(0), { type: "notiz", x: 5, y: 6 }, 42, "x"));
    expect(card).toMatchObject({ id: "x", boardId: "root", type: "notiz", x: 5, y: 6, title: "", text: "", image: null, fields: {}, updatedAt: 42, deletedAt: null });
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
