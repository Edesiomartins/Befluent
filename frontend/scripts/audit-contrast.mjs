import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { chromium } from "@playwright/test";

const require = createRequire(import.meta.url);
const axePath = require.resolve("axe-core/axe.min.js");
const root = path.resolve(import.meta.dirname, "../..");
const outFile = path.join(root, "docs", "layout-v1", "axe-contrast-report.json");
const base = "http://127.0.0.1:3011";

async function loginOrOnboard(page) {
  const email = process.env.LAYOUT_EMAIL || "layout-before-1792811502013@example.com";
  const password = "Senha12345";
  await page.goto(`${base}/login`);
  await page.getByLabel("E-mail").fill(email);
  await page.getByRole("textbox", { name: "Senha", exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 30_000 });
}

async function runAxe(page, screenName, viewportName) {
  await page.addScriptTag({ path: axePath });
  const results = await page.evaluate(async () => {
    function parseRgba(str) {
      const m = str.match(/rgba?\(([^)]+)\)/);
      if (!m) return [0, 0, 0, 0];
      const parts = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
      return [parts[0] ?? 0, parts[1] ?? 0, parts[2] ?? 0, parts[3] ?? 1];
    }
    function blend(fg, bg) {
      const a = fg[3];
      if (a >= 1) return [fg[0], fg[1], fg[2], 1];
      return [
        fg[0] * a + bg[0] * (1 - a),
        fg[1] * a + bg[1] * (1 - a),
        fg[2] * a + bg[2] * (1 - a),
        1,
      ];
    }
    function lum(rgb) {
      const [r, g, b] = rgb.map((c) => {
        const s = c / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
    function ratio(a, b) {
      const l1 = Math.max(lum(a), lum(b));
      const l2 = Math.min(lum(a), lum(b));
      return (l1 + 0.05) / (l2 + 0.05);
    }

    // Measure every visible text element inside dark command surfaces (sidebar, header, .command-panel)
    // against both its composited background-color and the worst-case .command-panel gradient peak
    const commandNodes = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    while (walker.nextNode()) {
      const el = walker.currentNode;
      if (!(el instanceof HTMLElement)) continue;
      const directText = Array.from(el.childNodes)
        .filter((n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim().length > 0)
        .map((n) => n.textContent.trim())
        .join(" ");
      if (!directText) continue;
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) continue;
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;

      const inCommand = el.closest(".command-panel, aside, header");
      if (!inCommand) continue;

      // Collect background chain up to root
      const chain = [];
      let cur = el;
      let insideCommandPanel = false;
      while (cur && cur instanceof HTMLElement) {
        if (cur.classList.contains("command-panel")) insideCommandPanel = true;
        const bg = parseRgba(window.getComputedStyle(cur).backgroundColor);
        if (bg[3] > 0) chain.push(bg);
        if (bg[3] >= 1) break;
        cur = cur.parentElement;
      }
      // Base canvas if not opaque
      let base = [243, 246, 251, 1];
      if (insideCommandPanel) {
        // Worst-case top-right glow on .command-panel: #111c33 blended with 26% #9a3412 (highest luminance accent)
        base = [17 * 0.74 + 154 * 0.26, 28 * 0.74 + 52 * 0.26, 51 * 0.74 + 18 * 0.26, 1];
      }
      for (let i = chain.length - 1; i >= 0; i -= 1) {
        if (insideCommandPanel && i === chain.length - 1 && chain[i][0] === 11 && chain[i][1] === 18 && chain[i][2] === 32) {
          continue;
        }
        base = blend(chain[i], base);
      }
      const fg = blend(parseRgba(style.color), base);
      const cRatio = Number(ratio(fg, base).toFixed(2));
      const fontSize = parseFloat(style.fontSize);
      commandNodes.push({
        text: directText.slice(0, 60),
        color: style.color,
        fontSize,
        contrast: cRatio,
        belowAA: cRatio < 4.5,
      });
    }

    // Run axe-core both with and without CSS gradients so axe also checks color-contrast inside .command-panel
    // @ts-expect-error axe injected on window
    const res = await window.axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
      },
    });

    const tag = document.createElement("style");
    tag.textContent = ".command-panel { background-image: none !important; background-color: var(--command-surface) !important; }";
    document.head.appendChild(tag);
    // @ts-expect-error axe injected on window
    const resNoGrad = await window.axe.run(document, {
      runOnly: {
        type: "rule",
        values: ["color-contrast"],
      },
    });
    tag.remove();

    return {
      violations: res.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          html: n.html.slice(0, 220),
          failureSummary: n.failureSummary,
        })),
      })),
      flatContrastViolations: resNoGrad.violations.flatMap((v) =>
        v.nodes.map((n) => ({
          target: n.target,
          html: n.html.slice(0, 220),
          failureSummary: n.failureSummary,
        })),
      ),
      lowCommandNodes: commandNodes.filter((n) => n.belowAA),
      minCommandContrast: commandNodes.reduce((min, n) => Math.min(min, n.contrast), 99),
      passesCount: res.passes.length,
    };
  });
  return {
    viewport: viewportName,
    screen: screenName,
    url: page.url(),
    violationsCount: results.violations.length,
    contrastViolationsCount:
      results.violations.filter((v) => v.id === "color-contrast").length +
      results.flatContrastViolations.length,
    violations: results.violations,
    flatContrastViolations: results.flatContrastViolations,
    lowCommandNodes: results.lowCommandNodes,
    minCommandContrast: results.minCommandContrast,
    passesCount: results.passesCount,
  };
}

async function auditViewport(browser, viewportName, viewport) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const entries = [];
  await loginOrOnboard(page);

  await page.goto(`${base}/dashboard`);
  await page.getByRole("heading").first().waitFor();
  entries.push(await runAxe(page, "dashboard", viewportName));

  await page.goto(`${base}/cronograma`);
  await page.getByRole("heading").first().waitFor();
  entries.push(await runAxe(page, "cronograma", viewportName));

  const dayLink = page.getByRole("link", { name: /Começar esta jornada|Continuar aprendendo/ });
  if (await dayLink.isVisible().catch(() => false)) {
    await dayLink.click();
    await page.waitForURL(/\/cronograma\/dia\//);
    await page.getByRole("heading").first().waitFor();
    await page.getByText("Verificando sua sessão").waitFor({ state: "hidden", timeout: 20_000 }).catch(() => undefined);
    await page
      .getByRole("button", { name: /Enviar tentativa|Continuar|Verificar/ })
      .or(page.getByRole("heading").first())
      .first()
      .waitFor();
    entries.push(await runAxe(page, "dia", viewportName));
  }

  await page.goto(`${base}/learn/vocabulary`);
  const ready = page
    .getByRole("button", { name: /Enviar tentativa|Continuar|Tentar novamente|Verificar|Sair|Dose do dia/ })
    .or(page.getByRole("heading", { name: /Sessão concluída|Vocabulário em dia/ }))
    .first();
  await ready.waitFor({ timeout: 60_000 });
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
  entries.push(await runAxe(page, "sessao", viewportName));

  const box = page.getByRole("textbox", { name: "Sua resposta" });
  const radios = page.getByRole("radio");
  if (!(await box.count()) && !(await radios.count())) {
    const cont = page.getByRole("button", { name: "Continuar" });
    if (await cont.isVisible().catch(() => false)) {
      await cont.click();
      await page.waitForTimeout(200);
    }
  }
  if (await box.count()) await box.fill("zzz");
  else if (await radios.count()) await radios.last().click();
  const action = page.getByRole("button", { name: /Enviar tentativa|Continuar|Verificar/ });
  if ((await box.count()) || (await radios.count())) {
    await action.click();
    await page.getByText(/Resposta incorreta|Correto\.|Correção da resposta anterior/).first().waitFor({ timeout: 20_000 });
  }
  entries.push(await runAxe(page, "feedback", viewportName));

  await page.goto(`${base}/progress`);
  await page.getByRole("heading").first().waitFor();
  entries.push(await runAxe(page, "progresso", viewportName));

  await context.close();
  return entries;
}

const browser = await chromium.launch();
const desktopEntries = await auditViewport(browser, "desktop", { width: 1280, height: 800 });
const mobileEntries = await auditViewport(browser, "mobile", { width: 390, height: 844 });
await browser.close();

const all = [...desktopEntries, ...mobileEntries];
fs.writeFileSync(outFile, JSON.stringify(all, null, 2));
for (const entry of all) {
  console.log(
    `${entry.viewport} ${entry.screen}: violations=${entry.violationsCount} flatContrast=${entry.flatContrastViolations.length} lowCommandNodes=${entry.lowCommandNodes.length} minCommandContrast=${entry.minCommandContrast}`,
  );
  for (const v of entry.violations) {
    console.log(`  - [${v.id}] (${v.impact}) nodes=${v.nodes.length}`);
  }
  for (const n of entry.flatContrastViolations) {
    console.log(`  - [flat-contrast] target=${JSON.stringify(n.target)} ${n.failureSummary?.replace(/\s+/g, " ")}`);
  }
  for (const n of entry.lowCommandNodes) {
    console.log(`  - [low-command] "${n.text}" contrast=${n.contrast} size=${n.fontSize}px`);
  }
}
