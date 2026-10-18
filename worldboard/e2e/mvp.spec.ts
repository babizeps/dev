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

test("Weltname direkt umbenennen; Punkt nur beim Speichern", async ({ page }) => {
  await page.goto("/");
  const name = page.getByRole("textbox", { name: "Name der Welt" });
  await expect(name).toHaveValue("Meine Welt");

  await name.fill("Die Glasküste");
  await page.keyboard.press("Enter");
  await expect(name).not.toBeFocused();

  // Der Status-Text ist nur für Screenreader da; gespeichert ist der Normalfall, dann kein Punkt
  const status = page.getByRole("status");
  await expect(status).toHaveText("Gespeichert");
  expect((await status.locator(".save-label").boundingBox())!.width).toBeLessThanOrEqual(1);
  await expect(status.locator(".save-dot")).toHaveCSS("opacity", "0");

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

test("Eigene Mauszeiger je Stil, auch für Text", async ({ page }) => {
  await page.goto("/");
  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  const card = page.getByTestId("card");
  await expect(card).toHaveCount(1);
  await waitSaved(page);
  const cursorOf = (sel: string) => page.locator(sel).first().evaluate((el) => getComputedStyle(el).cursor);

  for (const style of ["studio", "sketch"]) {
    await page.evaluate((s) => localStorage.setItem("worldboard.style", s), style);
    await page.reload();
    const pane = await cursorOf(".react-flow__pane");
    expect(pane, style).toContain("data:image/svg+xml");
    expect(await cursorOf(".react-flow__node"), style).toBe(pane);
    expect(await cursorOf(".card-type"), style).toBe(pane);
    const text = await cursorOf(".card-title");
    expect(text, style).toContain("data:image/svg+xml");
    expect(text, style).toMatch(/, text$/);
    expect(text, style).not.toBe(pane);
  }
  // Studio und Skizzenbuch haben unterschiedliche Zeiger
  await page.evaluate(() => localStorage.setItem("worldboard.style", "studio"));
  await page.reload();
  const studio = await cursorOf(".react-flow__pane");
  await page.evaluate(() => localStorage.setItem("worldboard.style", "sketch"));
  await page.reload();
  expect(await cursorOf(".react-flow__pane")).not.toBe(studio);
});

test("Beim Verbinden zeigt die Leinwand das Plus des Stils", async ({ page }) => {
  await page.goto("/");
  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  await expect(page.getByTestId("card")).toHaveCount(1);
  const cursorOf = (sel: string) => page.locator(sel).first().evaluate((el) => getComputedStyle(el).cursor);

  const handleCursor = await cursorOf(".handle-source");
  expect(handleCursor).toContain("data:image/svg+xml");
  expect(handleCursor).toMatch(/, crosshair$/);
  expect(await cursorOf(".react-flow__pane")).not.toBe(handleCursor);

  await page.getByTestId("card").hover();
  const box = (await page.locator(".handle-source").boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + 200, box.y + 120, { steps: 5 });
  await expect(page.locator(".react-flow.is-connecting")).toHaveCount(1);
  expect(await cursorOf(".react-flow__pane")).toBe(handleCursor);
  await page.mouse.up();
  await expect(page.locator(".react-flow.is-connecting")).toHaveCount(0);
});

test("Zoom: bei 100 % unsichtbar, ein Klick setzt auf 100 % zurück", async ({ page }) => {
  await page.goto("/");
  const zoom = page.locator(".zoom");
  await expect(zoom).toHaveClass(/is-hidden/);

  // Zwei weit auseinander liegende Karten, dann herauszoomen
  const pane = page.locator(".react-flow__pane");
  await pane.dblclick({ position: { x: 150, y: 150 } });
  await page.keyboard.press("Escape");
  await pane.dblclick({ position: { x: 1100, y: 600 } });
  await page.keyboard.press("Escape");
  await page.mouse.move(640, 360);
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, 400);
  await page.keyboard.up("Control");

  await expect(zoom).not.toHaveClass(/is-hidden/);
  // Ein Klick setzt genau auf 100 % zurück
  await zoom.getByRole("button").click();
  await expect(zoom).toHaveClass(/is-hidden/);
  await expect(page.locator(".react-flow__viewport")).toHaveCSS("transform", /^matrix\(1, 0, 0, 1, /);
});

test("Trackpad: zwei Finger schieben die Leinwand, ohne zu zoomen", async ({ page }) => {
  await page.goto("/");
  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  await page.keyboard.press("Escape");
  const transform = () => page.locator(".react-flow__viewport").evaluate((el) => getComputedStyle(el).transform);
  const before = await transform();
  await page.mouse.move(640, 360);
  await page.mouse.wheel(120, 80);
  await expect.poll(transform).not.toBe(before);
  // Maßstab bleibt 1, und die Leinwand folgt den Fingern 1:1
  const [, , , , x0, y0] = before.match(/-?[\d.]+/g)!.map(Number);
  await expect.poll(async () => (await transform()).match(/-?[\d.]+/g)!.map(Number)).toEqual([1, 0, 0, 1, x0 - 120, y0 - 80]);
  await expect(page.locator(".zoom")).toHaveClass(/is-hidden/);
});

test("Trackpad: Schieben klappt auch, wenn der Zeiger über einer Karte steht", async ({ page }) => {
  await page.goto("/");
  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  await page.keyboard.type("Titel");
  await page.keyboard.press("Escape");
  const transform = () => page.locator(".react-flow__viewport").evaluate((el) => getComputedStyle(el).transform);
  const nums = async () => (await transform()).match(/-?[\d.]+/g)!.map(Number);
  for (const part of [".card-title", ".card-text", ".card-type"]) {
    const [, , , , x0, y0] = await nums();
    const box = (await page.locator(part).first().boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(40, 30);
    await expect.poll(nums, part).toEqual([1, 0, 0, 1, x0 - 40, y0 - 30]);
    await page.waitForTimeout(300);
  }
});

test("Dock: jeder Typ-Knopf leuchtet beim Darüberfahren auf, auch Notiz im Skizzenbuch", async ({ page }) => {
  for (const style of ["studio", "sketch"]) {
    for (const mode of ["light", "dark"]) {
      await page.goto("/");
      await page.evaluate(([s, m]) => { localStorage.setItem("worldboard.style", s); localStorage.setItem("worldboard.mode", m); }, [style, mode]);
      await page.reload();
      const dock = page.locator(".dock");
      const surface = await dock.evaluate((el) => getComputedStyle(el).backgroundColor);
      for (const btn of await page.locator(".dock-btn[data-type]").all()) {
        await btn.hover();
        const bg = await btn.evaluate((el) => getComputedStyle(el).backgroundColor);
        expect(bg, `${style}/${mode} ${await btn.getAttribute("data-type")}`).not.toBe(surface);
      }
    }
  }
});

test("Weltname und Ansicht sind nur beim Darüberfahren zu sehen", async ({ page }) => {
  for (const style of ["studio", "sketch"]) {
    await page.goto("/");
    await page.evaluate((s) => localStorage.setItem("worldboard.style", s), style);
    await page.reload();
    const title = page.locator(".title-island");
    const status = page.locator(".status-island");
    await page.mouse.move(640, 400);
    await expect(title, style).toHaveCSS("opacity", "0");
    await expect(status, style).toHaveCSS("opacity", "0");
    // Keine Insel mehr: durchsichtig, ohne Rahmen
    await expect(title).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
    await expect(page.locator(".brand-name")).toHaveCount(0);

    await title.hover();
    await expect(title, style).toHaveCSS("opacity", "1");
    await status.hover();
    await expect(status, style).toHaveCSS("opacity", "1");

    // Offenes Ansicht-Menü hält die Ecke sichtbar, auch wenn die Maus weggeht
    await page.getByRole("button", { name: "Ansicht" }).click();
    await page.mouse.move(640, 600);
    await expect(status, style).toHaveCSS("opacity", "1");
    // Klick daneben schließt das Menü, dann verschwindet die Ecke wieder
    await page.locator(".react-flow__pane").click({ position: { x: 640, y: 600 } });
    await expect(page.getByRole("dialog", { name: "Ansicht" })).toBeHidden();
    await expect(status, style).toHaveCSS("opacity", "0");

    // Beim Umbenennen bleibt der Name sichtbar
    await page.getByRole("textbox", { name: "Name der Welt" }).focus();
    await page.mouse.move(640, 400);
    await expect(title, style).toHaveCSS("opacity", "1");
  }
});

test("Skizzenbuch: Dock und Typ-Menü wie aus dem Skizzenbuch", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("worldboard.style", "sketch"));
  await page.reload();
  const dockBtn = page.locator('.dock-btn[data-type="figur"]');
  // Kein System-Tooltip mehr, die Beschriftung steht schon da
  await expect(dockBtn).not.toHaveAttribute("title");
  // Textmarker statt Fläche
  await dockBtn.hover();
  await expect(dockBtn).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect.poll(() => dockBtn.locator("span").evaluate((el) => getComputedStyle(el, "::before").transform)).not.toContain("matrix(0,");

  // Typ-Menü: Handschrift, eingekreister Typ, Ziffern nur unter der Maus
  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  await page.keyboard.press("Escape");
  await page.getByTestId("card").getByRole("button", { name: /^Kartentyp/ }).click();
  const menu = page.getByRole("menu", { name: "Kartentyp" });
  await expect(menu).toBeVisible();
  expect(await menu.evaluate((el) => getComputedStyle(el).fontFamily)).toContain("Caveat");
  const checked = menu.locator('[aria-checked="true"]');
  await expect(checked.locator(".card-menu-check")).toBeHidden();
  expect(await checked.locator(".type-chip").evaluate((el) => getComputedStyle(el, "::after").content)).toBe('""');
  const ort = menu.locator('[data-type="ort"]');
  await expect(ort.locator("kbd")).toHaveCSS("opacity", "0");
  await ort.hover();
  await expect(ort.locator("kbd")).not.toHaveCSS("opacity", "0");
});

test("Skizzenbuch: Karte in Handschrift, Textmarker beim Schreiben, Ansicht-Menü als Zettel", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("worldboard.style", "sketch"));
  await page.reload();
  await page.locator(".react-flow__pane").dblclick({ position: { x: 400, y: 300 } });
  const text = page.getByTestId("card").getByRole("textbox", { name: "Beschreibung" });
  for (const el of [text, page.getByTestId("card").getByRole("button", { name: /^Kartentyp/ })]) {
    expect(await el.evaluate((e) => getComputedStyle(e).fontFamily)).toContain("Caveat");
  }
  // Langer Text wird nicht abgeschnitten
  await text.fill("Kartografin aus Vel Amar. Kennt jeden Pass im Nordgebirge und schuldet der Gilde noch drei Karten.");
  expect(await text.evaluate((e) => e.scrollHeight - e.clientHeight)).toBeLessThanOrEqual(1);
  // Fokus: Textmarker statt Linie
  await expect(text).toHaveCSS("box-shadow", "none");
  expect(await text.evaluate((e) => getComputedStyle(e).backgroundColor)).not.toBe("rgba(0, 0, 0, 0)");
  await page.keyboard.press("Escape");

  await page.locator(".status-island").hover();
  await page.getByRole("button", { name: "Ansicht" }).click();
  const selected = page.getByRole("button", { name: "Skizzenbuch" });
  await expect(selected).toHaveAttribute("aria-pressed", "true");
  expect(await selected.evaluate((e) => getComputedStyle(e, "::after").opacity)).toBe("1");
  expect(await page.locator(".view-menu-label").first().evaluate((e) => getComputedStyle(e).fontFamily)).toContain("Caveat");
});

test("Skizzenbuch: Tinte statt Violett, gekritzelter Verbindungspunkt, Rötel-Schimmer am Ziel", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("worldboard.style", "sketch"));
  await page.reload();
  const pane = page.locator(".react-flow__pane");
  await pane.dblclick({ position: { x: 300, y: 250 } });
  await page.keyboard.press("Escape");
  await pane.dblclick({ position: { x: 800, y: 450 } });
  await page.keyboard.press("Escape");
  const cards = page.getByTestId("card");
  await expect(cards).toHaveCount(2);

  const accent = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--accent").trim());
  expect(accent).toBe("#26251f");
  const handle = page.locator(".handle-source").first();
  expect(await handle.evaluate((e) => getComputedStyle(e).backgroundImage)).toContain("svg");
  await expect(handle).toHaveCSS("border-top-width", "0px");

  await cards.nth(0).hover();
  const h = (await handle.boundingBox())!;
  const target = (await cards.nth(1).boundingBox())!;
  await page.mouse.move(h.x + h.width / 2, h.y + h.height / 2);
  await page.mouse.down();
  await page.mouse.move(target.x + target.width / 2, target.y + target.height / 2, { steps: 8 });
  const glowing = page.locator(".card.is-connect-hover");
  await expect(glowing).toHaveCount(1);
  expect(await glowing.evaluate((e) => getComputedStyle(e).boxShadow)).toContain("rgba(194, 85, 45");
  await page.mouse.up();
});

test("Skizzenbuch: Verbindungslinien sind von Hand gezogen, Studio bleibt glatt", async ({ page }) => {
  await page.goto("/");
  const pane = page.locator(".react-flow__pane");
  await pane.dblclick({ position: { x: 300, y: 250 } });
  await page.keyboard.press("Escape");
  await pane.dblclick({ position: { x: 850, y: 450 } });
  await page.keyboard.press("Escape");
  const cards = page.getByTestId("card");
  await cards.nth(0).hover();
  const h = (await page.locator(".handle-source").first().boundingBox())!;
  const t = (await cards.nth(1).boundingBox())!;
  await page.mouse.move(h.x + h.width / 2, h.y + h.height / 2);
  await page.mouse.down();
  await page.mouse.move(t.x + t.width / 2, t.y + t.height / 2, { steps: 8 });
  await page.mouse.up();
  const edge = page.locator(".react-flow__edge-path").first();
  await expect(edge).toHaveCount(1);
  // Studio: eine glatte Bezierkurve (ein einziges C-Segment)
  expect((await edge.getAttribute("d"))!.match(/[CQ]/g)!.length).toBe(1);

  await waitSaved(page);
  await page.evaluate(() => localStorage.setItem("worldboard.style", "sketch"));
  await page.reload();
  await expect(page.locator(".react-flow__edge-path")).toHaveCount(1);
  const sketchD = (await page.locator(".react-flow__edge-path").first().getAttribute("d"))!;
  // Skizzenbuch: viele kleine Bögen statt einer Kurve – und beim Neuladen genau gleich
  expect(sketchD.match(/Q/g)!.length).toBeGreaterThan(20);
  await page.reload();
  expect(await page.locator(".react-flow__edge-path").first().getAttribute("d")).toBe(sketchD);
});
