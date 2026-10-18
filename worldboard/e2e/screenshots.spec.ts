import { test, type Page } from "@playwright/test";

/*
 * Erzeugt die Screenshots in docs/ mit einer Beispielwelt.
 * Läuft nur auf Wunsch: SCREENSHOTS=1 npm run test:e2e -- screenshots
 */
test.skip(!process.env.SCREENSHOTS, "nur mit SCREENSHOTS=1");

async function seed(page: Page) {
  await page.evaluate(async () => {
    async function picture(draw: (ctx: CanvasRenderingContext2D) => void) {
      const canvas = document.createElement("canvas");
      canvas.width = 520;
      canvas.height = 300;
      draw(canvas.getContext("2d")!);
      const blob = await new Promise<Blob>((r) => canvas.toBlob((b) => r(b!), "image/png"));
      const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
      const name = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("") + ".png";
      return { name, blob };
    }

    const harbor = await picture((ctx) => {
      ctx.fillStyle = "#b9c6c9";
      ctx.fillRect(0, 0, 520, 300);
      ctx.fillStyle = "#8fa3a8";
      ctx.fillRect(0, 190, 520, 110);
      ctx.fillStyle = "#5d7378";
      ctx.fillRect(60, 120, 90, 70);
      ctx.fillRect(170, 140, 120, 50);
      ctx.fillStyle = "#e9e4d6";
      ctx.fillRect(400, 60, 26, 130);
      ctx.fillStyle = "#d9a02b";
      ctx.fillRect(396, 48, 34, 16);
      ctx.fillStyle = "rgba(255,255,255,.35)";
      ctx.fillRect(0, 150, 520, 40);
    });

    const now = Date.now();
    const card = (id: string, type: string, x: number, y: number, title: string, text: string, image: string | null = null) =>
      ({ id, boardId: "root", type, x, y, title, text, image, fields: {}, updatedAt: now, deletedAt: null });
    const edge = (id: string, from: string, to: string) =>
      ({ id, boardId: "root", from, to, label: "", updatedAt: now, deletedAt: null });

    const world = {
      schemaVersion: 1,
      boards: [{ id: "root", name: "Die Glasküste", parentId: null, updatedAt: now, deletedAt: null }],
      cards: [
        card("mira", "figur", 110, 140, "Mira Vell", "Schmugglerin. Kennt jede Bucht der Glasküste."),
        card("hafen", "ort", 480, 60, "Hafen von Saltmere", "Nebelhafen, Umschlagplatz für Glasperlen.", harbor.name),
        card("gilde", "fraktion", 880, 150, "Die Lotsengilde", "Kontrolliert alle Fahrrinnen und verlangt Zoll."),
        card("sturm", "ereignis", 500, 470, "Die Sturmnacht", "Der Leuchtturm erlosch zum ersten Mal seit hundert Jahren."),
        card("idee", "notiz", 110, 470, "Idee", "Was, wenn das Glas Erinnerungen speichert?"),
        card("kompass", "gegenstand", 880, 470, "Der Lotsenkompass", "Zeigt nicht nach Norden, sondern zur nächsten Lüge."),
      ],
      edges: [edge("e1", "mira", "hafen"), edge("e2", "gilde", "hafen"), edge("e3", "sturm", "hafen"), edge("e4", "mira", "sturm"), edge("e5", "gilde", "kompass")],
    };

    const db = await new Promise<IDBDatabase>((resolve, reject) => {
      const req = indexedDB.open("worldboard", 1);
      req.onupgradeneeded = () => {
        req.result.createObjectStore("world");
        req.result.createObjectStore("assets");
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(["world", "assets"], "readwrite");
      tx.objectStore("world").put(world, "current");
      tx.objectStore("assets").put(harbor.blob, harbor.name);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  });
}

const THEMES = [
  ["studio", "light"],
  ["studio", "dark"],
  ["sketch", "light"],
  ["sketch", "dark"],
] as const;

test("Screenshots aller Themes", async ({ page }) => {
  await page.goto("/");
  await seed(page);
  for (const [style, mode] of THEMES) {
    await page.evaluate(
      ([s, m]) => {
        localStorage.setItem("worldboard.style", s);
        localStorage.setItem("worldboard.mode", m);
      },
      [style, mode],
    );
    await page.reload();
    await page.getByTestId("card").nth(5).waitFor();
    await page.locator(".card-image img").waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.mouse.move(5, 790);
    await page.waitForTimeout(400);
    await page.screenshot({ path: `docs/${style}-${mode}.png` });
  }
});
