import { expect, test } from "@playwright/test";

for (const viewport of [{ width: 1280, height: 720 }, { width: 1920, height: 1080 }]) {
  test(`historical defense presentation at ${viewport.width}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/research/defense");
    await page.getByRole("button", { name: "Apresentar à banca" }).click();
    for (let slide = 0; slide < 4; slide++) {
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      const fits = await page.locator("main").evaluate(el => el.scrollHeight <= window.innerHeight);
      expect(fits).toBe(true);
      await page.screenshot({ path: test.info().outputPath(`screen-${slide + 1}.png`) });
      if (slide === 1) await expect(page.getByText("61,5% · 123/200")).toBeVisible();
      if (slide < 3) await page.keyboard.press("ArrowRight");
    }
    await page.getByRole("button", { name: "Ver detalhes e fontes" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Apresentar à banca" })).toBeVisible();
  });
}
