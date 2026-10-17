import { describe, expect, it } from "vitest";
import { migrate, ROOT_BOARD_ID, UnsupportedSchemaError } from "./migrations";

describe("migrate", () => {
  it("liefert eine leere Welt, wenn noch nichts gespeichert ist", () => {
    const w = migrate(null);
    expect(w.schemaVersion).toBe(1);
    expect(w.boards.map((b) => b.id)).toEqual([ROOT_BOARD_ID]);
    expect(w.cards).toEqual([]);
  });

  it("ergänzt fehlende Felder und korrigiert unbekannte Typen", () => {
    const w = migrate({ cards: [{ id: "a", type: "drache", x: 3 }], edges: [{ id: "e", from: "a", to: "a" }, { id: "kaputt" }] });
    expect(w.cards[0]).toEqual({ id: "a", boardId: "root", type: "notiz", x: 3, y: 0, title: "", text: "", image: null, fields: {}, updatedAt: 0, deletedAt: null });
    expect(w.edges.map((e) => e.id)).toEqual(["e"]);
    expect(w.boards[0].id).toBe(ROOT_BOARD_ID);
  });

  it("lehnt eine neuere Format-Version ab, statt sie zu überschreiben", () => {
    expect(() => migrate({ schemaVersion: 2, cards: [] })).toThrow(UnsupportedSchemaError);
  });

  it("gibt eine gültige Welt unverändert zurück", () => {
    const valid = migrate({ schemaVersion: 1, cards: [{ id: "a", type: "ort", title: "Hafen", updatedAt: 5, deletedAt: 7 }] });
    expect(migrate(JSON.parse(JSON.stringify(valid)))).toEqual(valid);
  });
});
