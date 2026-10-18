import { expect, test, type Page } from "@playwright/test";

async function newCard(page: Page, x: number, y: number, title: string) {
  const cards = page.getByTestId("card");
  const index = await cards.count();
  await page.locator(".react-flow__pane").dblclick({ position: { x, y } });
  // Feste Position statt .last(), sonst zeigt der Locator nach der nächsten neuen Karte auf diese.
  const card = cards.nth(index);
  await expect(card.getByLabel("Titel")).toBeFocused();
  await page.keyboard.type(title);
  return card;
}

/** Karte auswählen, ohne in ein Textfeld zu klicken. */
async function select(card: ReturnType<Page["getByTestId"]>) {
  await card.click({ position: { x: 240, y: 10 } });
}

test("Keine Leiste über der Karte und kein eigenes Rechtsklick-Menü", async ({ page }) => {
  await page.goto("/");
  const card = await newCard(page, 400, 350, "Mira");
  await select(card);
  await expect(page.locator(".react-flow__node-toolbar")).toHaveCount(0);
  await card.click({ button: "right", position: { x: 240, y: 10 } });
  await expect(page.getByRole("menu")).toHaveCount(0);
});

test("Menü an der Plakette mit Tastatur und Escape", async ({ page }) => {
  await page.goto("/");
  const card = await newCard(page, 400, 350, "Hafen");
  const badge = card.getByRole("button", { name: /^Kartentyp/ });

  await badge.click();
  const menu = page.getByRole("menu", { name: "Kartentyp" });
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("menuitemradio", { name: "Notiz" })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(menu).toBeHidden();
  await expect(card).toHaveAttribute("data-type", "ort");
  await expect(badge).toHaveAccessibleName("Kartentyp: Ort");

  await badge.click();
  await page.keyboard.press("Escape");
  await expect(menu).toBeHidden();

  // Klick daneben schließt ebenfalls
  await badge.click();
  await page.locator(".react-flow__pane").click({ position: { x: 900, y: 650 } });
  await expect(menu).toBeHidden();
});

test("Tasten 1–6 und Strg+D, aber nicht beim Tippen", async ({ page }) => {
  await page.goto("/");
  const cards = page.getByTestId("card");
  const card = await newCard(page, 400, 350, "Gilde");

  // Im Titel getippte Ziffern bleiben Text
  await page.keyboard.type(" 4");
  await expect(card.getByLabel("Titel")).toHaveValue("Gilde 4");
  await expect(card).toHaveAttribute("data-type", "notiz");

  await select(card);
  await page.keyboard.press("4");
  await expect(card).toHaveAttribute("data-type", "fraktion");
  await page.keyboard.press("Control+d");
  await expect(cards).toHaveCount(2);

  // Rückgängig macht das Duplizieren und den Typwechsel einzeln rückgängig
  await page.keyboard.press("Control+z");
  await expect(cards).toHaveCount(1);
  await page.keyboard.press("Control+z");
  await expect(card).toHaveAttribute("data-type", "notiz");
});
