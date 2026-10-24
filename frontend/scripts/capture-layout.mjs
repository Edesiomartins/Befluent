import fs from "node:fs";
import path from "node:path";
import { chromium } from "@playwright/test";

const root = path.resolve(import.meta.dirname, "../..");
const phase = process.argv[2] === "after" ? "after" : "before";
const outDir = path.join(root, "docs", "layout-v1", phase);
const base = "http://127.0.0.1:3011";

fs.mkdirSync(outDir, { recursive: true });

async function onboard(page) {
  const email = process.env.LAYOUT_EMAIL || `layout-${phase}-${Date.now()}@example.com`;
  const password = "Senha12345";
  if (!process.env.LAYOUT_EMAIL) {
    await page.goto(`${base}/register`);
    await page.getByLabel("Nome").fill("Aluno Layout");
    await page.getByLabel("E-mail").fill(email);
    await page.getByRole("textbox", { name: "Senha", exact: true }).fill(password);
    await page.getByLabel("Confirmar senha").fill(password);
    await page.getByRole("button", { name: "Criar minha conta" }).click();
    await page.waitForURL(/\/login/);
  } else {
    await page.goto(`${base}/login`);
  }
  await page.getByLabel("E-mail").fill(email);
  await page.getByRole("textbox", { name: "Senha", exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/(dashboard|onboarding)/);
  if (process.env.LAYOUT_EMAIL && page.url().includes("/dashboard")) return;
  if (!page.url().includes("/onboarding")) await page.goto(`${base}/onboarding`);
  const native = page.locator("#onboarding-native-language");
  const french = page.getByText("Francês", { exact: true });
  await native.or(french).first().waitFor();
  if (await native.isVisible().catch(() => false)) {
    await native.selectOption("pt-BR");
    await page.getByRole("button", { name: "Continuar" }).click();
  } else {
    await native.waitFor({ timeout: 8_000 }).catch(() => undefined);
    if (await native.isVisible().catch(() => false)) {
      await native.selectOption("pt-BR");
      await page.getByRole("button", { name: "Continuar" }).click();
    }
  }
  await french.click();
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByText("Prefiro informar meu nível", { exact: true }).click();
  await page.locator("select").selectOption("B1");
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByText("Viajar", { exact: true }).click();
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Criar meu plano" }).click();
  await page.waitForURL(/\/(dashboard|cronograma|learn)/, { timeout: 60_000 });
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name), fullPage: true });
  console.log(name);
}

async function captureShell(page, prefix) {
  await page.goto(`${base}/dashboard`);
  await page.getByRole("heading").first().waitFor();
  await shot(page, `${prefix}-dashboard.png`);
  await page.goto(`${base}/cronograma`);
  await page.getByRole("heading").first().waitFor();
  await shot(page, `${prefix}-cronograma.png`);
  const day = page.getByRole("link", { name: /Começar esta jornada|Continuar aprendendo/ });
  if (await day.isVisible().catch(() => false)) {
    await day.click();
    await page.waitForURL(/\/cronograma\/dia\//);
    await page.getByRole("heading").first().waitFor();
    await page.getByText("Verificando sua sessão").waitFor({ state: "hidden", timeout: 20_000 }).catch(() => undefined);
    await shot(page, `${prefix}-cronograma-dia.png`);
  }
  await page.goto(`${base}/progress`);
  await page.getByRole("heading").first().waitFor();
  await shot(page, `${prefix}-progresso.png`);
}

async function openPractice(page) {
  await page.goto(`${base}/learn/vocabulary`);
  const ready = page
    .getByRole("button", { name: /Enviar tentativa|Continuar|Tentar novamente|Verificar|Sair|Dose do dia/ })
    .or(page.getByRole("heading", { name: /Sessão concluída|Vocabulário em dia/ }))
    .first();
  await ready.waitFor({ timeout: 90_000 });
  if (await page.getByRole("heading", { name: "Vocabulário em dia" }).isVisible().catch(() => false)) {
    await page.goto(`${base}/dashboard`);
    await page.getByRole("link", { name: "Continuar a missão de hoje" }).click();
    await page.waitForURL(/\/cronograma\/dia\//);
    await page
      .getByRole("button", { name: /Enviar tentativa|Continuar|Verificar/ })
      .or(page.getByRole("heading").first())
      .first()
      .waitFor();
  }
}

async function capturePractice(page, prefix) {
  await openPractice(page);
  if (await page.getByRole("heading", { name: "Sessão concluída" }).isVisible()) {
    const again = page.getByRole("button", { name: "Dose do dia" });
    if (await again.isVisible()) await again.click();
    await page.getByRole("button", { name: /Enviar tentativa|Continuar|Verificar/ }).waitFor();
  }
  await shot(page, `${prefix}-sessao.png`);

  const box = page.getByRole("textbox", { name: "Sua resposta" });
  const radios = page.getByRole("radio");
  if (await box.count()) await box.fill("zzz");
  else if (await radios.count()) await radios.last().click();
  const action = page.getByRole("button", { name: /Enviar tentativa|Continuar|Verificar/ });
  if (await box.count() || (await radios.count())) {
    await action.click();
    await page.getByText(/Resposta incorreta|Correto\.|Correção da resposta anterior/).waitFor({ timeout: 20_000 });
    await shot(page, `${prefix}-feedback.png`);
  } else {
    await shot(page, `${prefix}-feedback.png`);
  }

  for (let step = 0; step < 24; step += 1) {
    if (await page.getByRole("heading", { name: "Sessão concluída" }).isVisible()) break;
    const revealed = page.locator("p", { hasText: "Resposta correta:" }).first();
    const answer = (await revealed.isVisible().catch(() => false))
      ? ((await revealed.textContent()) ?? "").replace(/^.*Resposta correta:\s*/, "").trim()
      : "";
    const field = page.getByRole("textbox", { name: "Sua resposta" });
    const options = page.getByRole("radio");
    const words = page.getByRole("group", { name: "Palavras disponíveis" });
    if (await field.count()) await field.fill(answer || "oui");
    else if (await options.count()) {
      const named = answer ? page.getByRole("radio", { name: answer }) : null;
      if (named && (await named.count())) await named.click();
      else await options.first().click();
    } else if (await words.count()) {
      const buttons = words.getByRole("button");
      while ((await buttons.count()) > 0) await buttons.first().click();
    }
    const next = page.getByRole("button", { name: /Enviar tentativa|Continuar|Verificar|Tentar novamente/ });
    if (!(await next.isVisible()) || !(await next.isEnabled())) break;
    await next.click();
    await page.waitForTimeout(250);
  }
  await page.getByRole("heading", { name: "Sessão concluída" }).waitFor({ timeout: 8_000 }).catch(() => undefined);
  await shot(page, `${prefix}-resumo.png`);
}

const browser = await chromium.launch();
const desktop = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const desktopPage = await desktop.newPage();
await onboard(desktopPage);
await captureShell(desktopPage, "desktop");
await capturePractice(desktopPage, "desktop");
await desktop.close();

const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
const mobilePage = await mobile.newPage();
await onboard(mobilePage);
await captureShell(mobilePage, "mobile");
await capturePractice(mobilePage, "mobile");
await mobile.close();
await browser.close();
console.log(`capturas em ${outDir}`);
