// Capture only synthetic runs already created by validate_agents_as_tools_api.py.
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "@playwright/test";

const evidenceDir = path.resolve(process.argv[2] ?? "");
if (!process.argv[2]) throw new Error("Provide the private evidence directory containing manifest.json");
const baseUrl = process.env.WEB_BASE_URL ?? "http://127.0.0.1:3100";
const manifest = JSON.parse(await fs.readFile(path.join(evidenceDir, "manifest.json"), "utf8"));
const screenshotsDir = path.join(evidenceDir, process.env.UI_CAPTURE_LABEL ?? "ui-verified");
await fs.mkdir(screenshotsDir, { mode: 0o700 });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const results = [];
try {
  for (const record of manifest.records) {
    // Isolate localStorage/UI state as well as data between captures.
    const context = await browser.newContext({ viewport: { width: 1500, height: 1100 } });
    const page = await context.newPage();
    await page.goto(`${baseUrl}/?conversationId=${record.conversationId}`);
    const toggle = page.getByTestId("flow-toggle");
    await toggle.waitFor({ state: "visible" });
    if (await toggle.getAttribute("aria-pressed") !== "true") await toggle.click();
    const flow = page.getByTestId("runtime-visual-centralized");
    await page.getByTestId("observed-agent-flow").waitFor({ state: "visible", timeout: 30000 });
    await flow.locator(".react-flow__node").first().waitFor({ state: "visible" });
    const labels = await flow.locator(".react-flow__node").allTextContents();
    if (labels.some((label) => /Streamer/.test(label))) throw new Error("Fabricated streamer node shown");
    if (labels.length !== record.agents.length) throw new Error(`Observed agent count mismatch for ${record.caseId}`);
    const screenshot = path.join(screenshotsDir, `${record.caseId}-ui.png`);
    await page.screenshot({ path: screenshot, fullPage: true });
    await fs.chmod(screenshot, 0o600);
    const specialist = flow.locator(".react-flow__node").filter({ hasText: /especialista executado/ }).first();
    const role = await specialist.getAttribute("data-id");
    const execution = JSON.parse(await fs.readFile(path.join(evidenceDir, `${record.caseId}-execution.json`), "utf8"));
    const output = execution.executionEvents.find((event) => event.eventFamily === "agent" && event.eventName === "completed" && event.actorName === role)?.payload?.outputText;
    if (!output) throw new Error(`No actual specialist output for ${record.caseId}`);
    await specialist.hover();
    await page.getByRole("button", { name: "agent.completed" }).first().click();
    const returnedText = page.getByText(output, { exact: true });
    await returnedText.waitFor({ state: "visible" });
    await returnedText.scrollIntoViewIfNeeded();
    const returnScreenshot = path.join(screenshotsDir, `${record.caseId}-ui-return.png`);
    await page.screenshot({ path: returnScreenshot, fullPage: true });
    await fs.chmod(returnScreenshot, 0o600);
    results.push({ caseId: record.caseId, observedNodeCount: labels.length, labels, specialistReturnVisible: true });
    await context.close();
  }
} finally {
  await browser.close();
  await fs.writeFile(path.join(screenshotsDir, "ui-verification.json"), JSON.stringify(results, null, 2) + "\n", { mode: 0o600 });
}
console.log(JSON.stringify({ verified: results.length }));
