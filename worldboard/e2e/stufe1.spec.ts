import { expect, test, type Page } from "@playwright/test";

async function newCardWithTitle(page: Page, x: number, y: number, title: string) {
  await page.locator(".react-flow__pane").dblclick({ position: { x, y } });
  const title_ = page.getByTestId("card").last().getByLabel("Titel");
  await expect(title_).toBeFocused();
  await page.keyboard.type(title);
  return page.getByTestId("card").last();
}

async function paste(page: Page, color: string) {
  await page.evaluate(async (fill) => {
    const canvas = document.createElement("canvas");
    canvas.width = 200;
    canvas.height = 120;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = fill;
    ctx.fillRect(0, 0, 200, 120);
    const blob = await new Promise<Blob>((r) => canvas.toBlob((b) => r(b!), "image/png"));
    const dt = new DataTransfer();
    dt.items.add(new File([blob], "bild.png", { type: "image/png" }));
    const target = document.activeElement ?? document.body;
    target.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
  }, color);
}

test("Rückgängig und Wiederholen per Tastatur und Knopf", async ({ page }) => {
  await page.goto("/");
  const cards = page.getByTestId("card");
  const undo = page.getByRole("button", { name: "Rückgängig" });
  const redo = page.getByRole("button", { name: "Wiederholen" });
  await expect(undo).toBeDisabled();

  const card = await newCardWithTitle(page, 400, 300, "Mira");
  await expect(undo).toBeEnabled();

  // Tippen ist ein Schritt, das Anlegen ein weiterer.
  await page.keyboard.press("Control+z");
  await expect(card.getByLabel("Titel")).toHaveValue("");
  await page.keyboard.press("Control+z");
  await expect(cards).toHaveCount(0);
  await expect(undo).toBeDisabled();

  await page.keyboard.press("Control+Shift+z");
  await expect(cards).toHaveCount(1);
  await redo.click();
  await expect(cards.first().getByLabel("Titel")).toHaveValue("Mira");
  await expect(redo).toBeDisabled();

  // Gelöschte Karte zurückholen
  await cards.first().click({ position: { x: 240, y: 10 } });
  await page.keyboard.press("Delete");
  await expect(cards).toHaveCount(0);
  await undo.click();
  await expect(cards).toHaveCount(1);
  await expect(page.getByRole("status")).toHaveText("Gespeichert");
  await page.reload();
  await expect(cards.first().getByLabel("Titel")).toHaveValue("Mira");
});

test("Bild per Strg+V einfügen", async ({ page }) => {
  await page.goto("/");
  const cards = page.getByTestId("card");

  // Während man in einer Karte schreibt, landet das Bild in dieser Karte.
  const card = await newCardWithTitle(page, 400, 300, "Hafen");
  await paste(page, "#2e8b6e");
  await expect(card.locator(".card-image img")).toBeVisible();
  await expect(cards).toHaveCount(1);

  // Ohne Fokus und Auswahl entsteht eine neue Karte mit dem Bild.
  await page.locator(".react-flow__pane").click({ position: { x: 900, y: 600 } });
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await paste(page, "#e0643b");
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(1).locator(".card-image img")).toBeVisible();

  await expect(page.getByRole("status")).toHaveText("Gespeichert");
  await page.reload();
  await expect(page.locator(".card-image img")).toHaveCount(2);
});

test("Kartenbreite ändern und behalten", async ({ page }) => {
  await page.goto("/");
  const card = await newCardWithTitle(page, 400, 300, "Breite Karte");
  const node = page.locator(".react-flow__node").first();
  await card.click({ position: { x: 240, y: 10 } });

  const before = (await node.boundingBox())!;
  expect(Math.round(before.width)).toBe(260);
  const grip = (await page.locator(".card-resize").boundingBox())!;
  await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
  await page.mouse.down();
  await page.mouse.move(grip.x + grip.width / 2 + 120, grip.y + grip.height / 2, { steps: 10 });
  await page.mouse.up();

  await expect.poll(async () => Math.round((await node.boundingBox())!.width)).toBeGreaterThan(360);
  await expect(page.getByRole("status")).toHaveText("Gespeichert");
  await page.reload();
  const after = (await page.locator(".react-flow__node").first().boundingBox())!;
  expect(Math.round(after.width)).toBeGreaterThan(360);
  expect(Math.round(after.width)).toBeLessThanOrEqual(640);

  // Breite ist ein eigener Rückgängig-Schritt – nach dem Neuladen ist der Verlauf leer.
  await expect(page.getByRole("button", { name: "Rückgängig" })).toBeDisabled();
});
