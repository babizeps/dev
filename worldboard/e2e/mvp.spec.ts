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
  await page.getByRole("button", { name: "Skizze" }).click();
  await page.getByRole("button", { name: "Nachtmodus" }).click();
  await expect(html).toHaveAttribute("data-style", "sketch");
  await expect(html).toHaveAttribute("data-mode", "dark");
  await page.reload();
  await expect(html).toHaveAttribute("data-style", "sketch");
  await expect(html).toHaveAttribute("data-mode", "dark");
  await page.getByRole("button", { name: "Studio" }).click();
  await page.getByRole("button", { name: "Tagmodus" }).click();
  await expect(html).toHaveAttribute("data-style", "studio");
  await expect(html).toHaveAttribute("data-mode", "light");
});
