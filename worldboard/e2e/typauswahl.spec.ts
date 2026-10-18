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

test("Farbpunkte über der ausgewählten Karte", async ({ page }) => {
  await page.goto("/");
  const card = await newCard(page, 400, 350, "Mira");
  const toolbar = page.locator(".card-toolbar");
  await expect(toolbar).toBeHidden();

  await select(card);
  await expect(toolbar).toBeVisible();
  await expect(toolbar.getByRole("button", { name: "Notiz" })).toHaveAttribute("aria-pressed", "true");
  await toolbar.getByRole("button", { name: "Figur" }).click();
  await expect(card).toHaveAttribute("data-type", "figur");
  await expect(toolbar.getByRole("button", { name: "Figur" })).toHaveAttribute("aria-pressed", "true");

  // Bei zwei ausgewählten Karten keine Leiste
  const other = await newCard(page, 800, 350, "Hafen");
  await select(other);
  // React Flow erkennt Strg über das Tastenereignis, nicht über den Klick selbst.
  await page.keyboard.down("Control");
  await card.click({ position: { x: 240, y: 10 } });
  await page.keyboard.up("Control");
  await expect(page.locator(".react-flow__node.selected")).toHaveCount(2);
  await expect(toolbar).toBeHidden();
});

test("Menü an der Plakette mit Tastatur und Escape", async ({ page }) => {
  await page.goto("/");
  const card = await newCard(page, 400, 350, "Hafen");
  const badge = card.getByRole("button", { name: /^Kartentyp/ });

  await badge.click();
  const menu = page.getByRole("menu", { name: "Kartentyp" });
  await expect(menu).toBeVisible();
  await expect(page.locator(".card-toolbar")).toBeHidden();
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

test("Rechtsklick-Menü: Typ, Duplizieren, Breite, Löschen", async ({ page }) => {
  await page.goto("/");
  const cards = page.getByTestId("card");
  const card = await newCard(page, 400, 350, "Mira");

  await card.click({ button: "right", position: { x: 240, y: 10 } });
  const menu = page.getByRole("menu", { name: "Karte" });
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("menuitem", { name: "Breite zurücksetzen" })).toBeDisabled();
  await menu.getByRole("button", { name: "Ereignis" }).click();
  await expect(card).toHaveAttribute("data-type", "ereignis");
  await expect(menu).toBeHidden();

  await card.click({ button: "right", position: { x: 240, y: 10 } });
  await menu.getByRole("menuitem", { name: "Duplizieren" }).click();
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(1).getByLabel("Titel")).toHaveValue("Mira");
  await expect(cards.nth(1)).toHaveAttribute("data-type", "ereignis");

  await cards.nth(1).click({ button: "right", position: { x: 240, y: 10 } });
  await menu.getByRole("menuitem", { name: "Löschen" }).click();
  await expect(cards).toHaveCount(1);

  // Auch über den ⋯-Knopf der Leiste erreichbar
  await select(card);
  await page.getByRole("button", { name: "Weitere Aktionen" }).click();
  await expect(menu).toBeVisible();
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
