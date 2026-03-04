import { defineConfig, devices } from "@playwright/test";

/**
 * ServiceMatrix E2Eテスト設定
 * テスト対象: http://localhost:3000 (開発サーバー)
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["html", { outputFolder: "playwright-report" }], ["list"]],

  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // CI以外では開発サーバーを自動起動しない（手動で起動済み想定）
  // webServer: process.env.CI ? { command: "npm run start", port: 3000 } : undefined,
});
