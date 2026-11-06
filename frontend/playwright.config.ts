import { defineConfig, devices } from "@playwright/test";

const api = "http://127.0.0.1:8011";
const web = "http://127.0.0.1:3011";

export default defineConfig({
  testDir: "./e2e",
  timeout: 360_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: web,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: {
      args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
    },
    permissions: ["microphone"],
  },
  projects: [{
    name: "chromium",
    use: {
      ...devices["Desktop Chrome"],
      permissions: ["microphone"],
      // Dispositivo falso do Chromium. Não valida fala nem audição humana.
      launchOptions: {
        args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"],
      },
    },
  }],
  webServer: [
    {
      command: "py -3 scripts/dev_sqlite.py",
      cwd: "../backend",
      url: `${api}/health`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        DATABASE_URL:
          "sqlite:///C:/Users/DrEdesio/Documents/PROJETOS/Befluent/backend/tmp/e2e-fr-b1.sqlite3",
        COOKIE_DOMAIN: "",
        COOKIE_SECURE: "false",
        AI_MOCK_MODE: "true",
        STT_PROVIDER: "mock",
        TTS_PROVIDER: "mock",
        FRONTEND_ORIGIN: web,
        FRONTEND_URL: web,
        PORT: "8011",
      },
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3011",
      url: web,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        NEXT_PUBLIC_API_URL: api,
      },
    },
  ],
});
