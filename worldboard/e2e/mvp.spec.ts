import { expect, test, type Locator, type Page } from "@playwright/test";

async function dropImage(page: Page, target: Locator, color: string) {
  const dataTransfer = await page.evaluateHandle(async (fill) => {
    const canvas = document.createElement("canvas");
    canvas.width = 240;
    canvas.height = 140;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = fill;
    ctx.fillRect(0, 0, 240, 140);
    const blob = await new Promise<Blob>((r) => canvas.toBlob((b) => r(b!), "image/png"));
    const dt = new DataTransfer();
    dt.items.add(new File([blob], "bild.png", { type: "image/png" }));
    return dt;
  }, color);
  await target.dispatchEvent("dragover", { dataTransfer });
  await target.dispatchEvent("drop", { dataTransfer });
}

/** Das Dock erscheint erst, wenn die Maus unten im Fenster ist. */
async function revealDock(page: Page) {
  const { height, width } = page.viewportSize()!;
  await page.mouse.move(width / 2, height - 10);
  await expect(page.locator(".dock")).not.toHaveClass(/is-hidden/);
}

async function waitSaved(page: Page) {
  await expect(page.getByRole("status")).toHaveText("Gespeichert");
}

test("Karten, Bild und Verbindung sind nach dem Neuladen noch da", async ({ page }) => {
  await page.goto("/");
  const cards = page.getByTestId("card");
  await expect(page.getByText("Doppelklick auf die Leinwand für eine neue Karte")).toBeVisible();

  // Karte 1 per Doppelklick; der Fokus liegt sofort im Titel.
  await page.locator(".react-flow__pane").dblclick({ position: { x: 300, y: 300 } });
  await expect(cards).toHaveCount(1);
  await expect(cards.nth(0).getByLabel("Titel")).toBeFocused();
  await page.keyboard.type("Mira Vell");
  const mira = cards.nth(0);
  await expect(mira.getByLabel("Titel")).toHaveValue("Mira Vell");
  await mira.getByLabel("Beschreibung").fill("Schmugglerin.\nKennt jede Bucht.");
  await mira.getByRole("button", { name: /^Kartentyp/ }).click();
  await page.getByRole("menuitemradio", { name: "Figur" }).click();
  await expect(mira).toHaveAttribute("data-type", "figur");

  // Karte 2 über die Werkzeugleiste
  await revealDock(page);
  await page.getByRole("navigation", { name: "Neue Karte" }).getByRole("button", { name: "Ort" }).click();
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(1).getByLabel("Titel")).toBeFocused();
  await page.keyboard.type("Hafen von Saltmere");
  const hafen = cards.nth(1);
  await expect(hafen.getByLabel("Titel")).toHaveValue("Hafen von Saltmere");
  await expect(hafen).toHaveAttribute("data-type", "ort");

  // Bild auf Karte 2 ziehen
  await dropImage(page, hafen, "#2e8b6e");
  await expect(hafen.locator(".card-image img")).toBeVisible();

  // Verbindung: Punkt rechts an Karte 1 auf Karte 2 ziehen
  await mira.hover();
  const handle = await mira.locator(".handle-source").boundingBox();
  const targetBox = await hafen.boundingBox();
  await page.mouse.move(handle!.x + handle!.width / 2, handle!.y + handle!.height / 2);
  await page.mouse.down();
  await page.mouse.move(targetBox!.x + targetBox!.width / 2, targetBox!.y + targetBox!.height - 20, { steps: 12 });
  await page.mouse.up();
  await expect(page.locator(".react-flow__edge")).toHaveCount(1);

  await waitSaved(page);
  await page.reload();

  await expect(cards).toHaveCount(2);
  await expect(mira.getByLabel("Titel")).toHaveValue("Mira Vell");
  await expect(mira.getByLabel("Beschreibung")).toHaveValue("Schmugglerin.\nKennt jede Bucht.");
  await expect(mira).toHaveAttribute("data-type", "figur");
  await expect(hafen.locator(".card-image img")).toBeVisible();
  await expect(page.locator(".react-flow__edge")).toHaveCount(1);

  // Karte auswählen und löschen: ihre Verbindung verschwindet mit.
  await mira.click({ position: { x: 240, y: 10 } });
  await page.keyboard.press("Delete");
  await expect(cards).toHaveCount(1);
  await expect(page.locator(".react-flow__edge")).toHaveCount(0);

  await waitSaved(page);
  await page.reload();
  await expect(cards).toHaveCount(1);
  await expect(cards.nth(0).getByLabel("Titel")).toHaveValue("Hafen von Saltmere");
});

test("Tippen im Text löscht keine Karte", async ({ page }) => {
  await page.goto("/");
  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  await expect(page.getByTestId("card").getByLabel("Titel")).toBeFocused();
  await page.keyboard.type("Abc");
  await page.keyboard.press("Backspace");
  await expect(page.getByTestId("card")).toHaveCount(1);
  await expect(page.getByTestId("card").getByLabel("Titel")).toHaveValue("Ab");
});

test("Stil und Modus werden gemerkt", async ({ page }) => {
  await page.goto("/");
  const html = page.locator("html");
  const view = page.getByRole("button", { name: "Ansicht" });
  await view.click();
  await page.getByRole("button", { name: "Skizze" }).click();
  await page.getByRole("button", { name: "Nachtmodus" }).click();
  await expect(html).toHaveAttribute("data-style", "sketch");
  await expect(html).toHaveAttribute("data-mode", "dark");
  await page.reload();
  await expect(html).toHaveAttribute("data-style", "sketch");
  await expect(html).toHaveAttribute("data-mode", "dark");
  await view.click();
  await page.getByRole("button", { name: "Studio" }).click();
  await page.getByRole("button", { name: "Tagmodus" }).click();
  // Escape schließt das Ansicht-Menü
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Ansicht" })).toBeHidden();
  await expect(html).toHaveAttribute("data-style", "studio");
  await expect(html).toHaveAttribute("data-mode", "light");
});

test("Dock: Symbole behalten ihre Größe und passen ins Fenster", async ({ page }) => {
  for (const style of ["studio", "sketch"]) {
    for (const width of [1440, 1280, 1100, 900]) {
      await page.setViewportSize({ width, height: 700 });
      await page.goto("/");
      await page.evaluate((s) => localStorage.setItem("worldboard.style", s), style);
      await page.reload();
      const nav = page.getByRole("navigation", { name: "Neue Karte" });
      const sizes = await nav.locator("svg").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().width)));
      expect(sizes, `${style} bei ${width}px`).toEqual([20, 20, 20, 20, 20, 20]);
      const dock = (await page.locator(".dock").boundingBox())!;
      expect(dock.x, `${style} bei ${width}px`).toBeGreaterThanOrEqual(0);
      expect(dock.x + dock.width, `${style} bei ${width}px`).toBeLessThanOrEqual(width);
      // Dock und Zoom überlappen nicht
      const zoom = (await page.locator(".zoom").boundingBox())!;
      const apart = dock.x + dock.width <= zoom.x || zoom.y + zoom.height <= dock.y;
      expect(apart, `${style} bei ${width}px`).toBe(true);
    }
  }
});

test("Weltname direkt umbenennen; Status nur als Punkt", async ({ page }) => {
  await page.goto("/");
  const name = page.getByRole("textbox", { name: "Name der Welt" });
  await expect(name).toHaveValue("Meine Welt");

  await name.fill("Die Glasküste");
  await page.keyboard.press("Enter");
  await expect(name).not.toBeFocused();

  // Der Status-Text ist nur für Screenreader da, sichtbar ist der Punkt
  const status = page.getByRole("status");
  await expect(status).toHaveText("Gespeichert");
  expect((await status.locator(".save-label").boundingBox())!.width).toBeLessThanOrEqual(1);
  await expect(status.locator(".save-dot")).toBeVisible();

  await page.reload();
  await expect(name).toHaveValue("Die Glasküste");

  // Ein leerer Name fällt beim Verlassen auf den Standard zurück
  await name.fill("");
  await name.blur();
  await expect(name).toHaveValue("Meine Welt");
});

test("Dock erscheint nur unten, bei leerer Welt immer", async ({ page }) => {
  await page.goto("/");
  const dock = page.locator(".dock");
  // Leere Welt: Dock sichtbar
  await page.mouse.move(640, 300);
  await expect(dock).not.toHaveClass(/is-hidden/);

  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  await expect(page.getByTestId("card")).toHaveCount(1);
  await page.mouse.move(640, 300);
  await expect(dock).toHaveClass(/is-hidden/);

  await page.mouse.move(640, 790);
  await expect(dock).not.toHaveClass(/is-hidden/);
  // Über dem Dock bleibt es offen, weiter oben verschwindet es wieder
  const box = (await dock.boundingBox())!;
  await page.mouse.move(box.x + 20, box.y + 5);
  await page.waitForTimeout(700);
  await expect(dock).not.toHaveClass(/is-hidden/);
  await page.mouse.move(640, 200);
  await expect(dock).toHaveClass(/is-hidden/);
});

test("Auto-Modus folgt dem System", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  const html = page.locator("html");
  // Ohne gespeicherte Wahl gilt Auto
  await expect(html).toHaveAttribute("data-mode", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(html).toHaveAttribute("data-mode", "light");

  await page.getByRole("button", { name: "Ansicht" }).click();
  await expect(page.getByRole("button", { name: "Automatisch wie das System" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Nachtmodus" }).click();
  await page.emulateMedia({ colorScheme: "light" });
  await expect(html).toHaveAttribute("data-mode", "dark");

  await page.getByRole("button", { name: "Automatisch wie das System" }).click();
  await expect(html).toHaveAttribute("data-mode", "light");
  await page.reload();
  await expect(html).toHaveAttribute("data-mode", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(html).toHaveAttribute("data-mode", "dark");
});
