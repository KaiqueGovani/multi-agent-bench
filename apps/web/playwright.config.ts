import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
    cwd: __dirname,
    reuseExistingServer: true,
    timeout: 120_000,
    url: "http://127.0.0.1:3100",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
});
