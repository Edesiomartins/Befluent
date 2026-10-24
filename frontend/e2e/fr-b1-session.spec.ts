import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

const evidenceDir = path.resolve(
  __dirname,
  "../../docs/learning-experience-v2/evidence",
);

test("sessão FR B1: acerto, erro, retry, ditado e resumo", async ({ page }) => {
  fs.mkdirSync(evidenceDir, { recursive: true });
  const lines: string[] = [];
  const note = (line: string) => {
    lines.push(line);
    console.log(line);
  };

  const email = `fr-b1-${Date.now()}@example.com`;
  const password = "Senha12345";

  await page.goto("/register");
  await page.getByLabel("Nome").fill("Aluno FR");
  await page.getByLabel("E-mail").fill(email);
  await page.getByRole("textbox", { name: "Senha", exact: true }).fill(password);
  await page.getByLabel("Confirmar senha").fill(password);
  await page.getByRole("button", { name: "Criar minha conta" }).click();
  await page.waitForURL(/\/login/);
  note("cadastro ok");

  await page.getByLabel("E-mail").fill(email);
  await page.getByRole("textbox", { name: "Senha", exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/(dashboard|onboarding)/);
  note(`depois do login: ${page.url()}`);

  if (!page.url().includes("/onboarding")) {
    await page.goto("/onboarding");
  }
  await expect(
    page.getByRole("heading", { name: /língua nativa|Qual idioma você quer estudar/ }),
  ).toBeVisible();
  const nativeHeading = page.getByRole("heading", { name: "Qual é sua língua nativa?" });
  if (await nativeHeading.isVisible()) {
    await page.locator("#onboarding-native-language").selectOption("pt-BR");
    await page.getByRole("button", { name: "Continuar" }).click();
    note("língua nativa pt-BR");
  }
  await page.getByText("Francês", { exact: true }).click();
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByText("Prefiro informar meu nível", { exact: true }).click();
  await page.locator("select").selectOption("B1");
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByText("Viajar", { exact: true }).click();
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Criar meu plano" }).click();
  await page.waitForURL(/\/(dashboard|cronograma|learn)/, { timeout: 60_000 });
  note(`plano criado: ${page.url()}`);

  await page.goto("/learn/vocabulary");
  const activityAction = page.getByRole("button", { name: /Enviar tentativa|Continuar|Tentar novamente/ });
  const finished = page.getByRole("heading", { name: "Sessão concluída" });
  const emptyCycle = page.getByRole("heading", { name: "Vocabulário em dia" });
  const cycleError = page.getByText(/Não foi possível|database is locked|erro interno/i);
  await activityAction.or(finished).or(emptyCycle).or(cycleError).first().waitFor({ timeout: 90_000 });

  if (await page.getByRole("heading", { name: "Vocabulário em dia" }).isVisible()) {
    note("BLOQUEIO: a lição gerada não abriu ciclo. A fatia FR B1 não entrou.");
    await page.screenshot({ path: path.join(evidenceDir, "fr-b1-sem-ciclo.png"), fullPage: true });
    fs.writeFileSync(path.join(evidenceDir, "fr-b1-session.log"), lines.join("\n"), "utf8");
    throw new Error("Vocabulário em dia antes de qualquer atividade");
  }
  if (await cycleError.isVisible() && !(await page.locator("[data-interaction-family]").count())) {
    const alert = await cycleError.first().innerText();
    note(`erro ao abrir vocabulário: ${alert}`);
    await page.screenshot({ path: path.join(evidenceDir, "fr-b1-erro.png"), fullPage: true });
    fs.writeFileSync(path.join(evidenceDir, "fr-b1-session.log"), lines.join("\n"), "utf8");
    throw new Error(alert);
  }

  await page.screenshot({ path: path.join(evidenceDir, "fr-b1-inicio.png"), fullPage: true });

  let sawWrong = false;
  let sawCorrect = false;
  let sawRetry = false;
  let sawDictation = false;
  const families = new Set<string>();

  let pendingWrong = "";

  for (let step = 0; step < 36; step += 1) {
    if (await page.getByRole("heading", { name: "Sessão concluída" }).isVisible()) break;
    const activity = page.locator("[data-interaction-family]").first();
    const family = await activity.getAttribute("data-interaction-family");
    const signature = `${family}|${((await activity.innerText().catch(() => "")) || "").slice(0, 140)}`;
    if (family) families.add(family);
    if (family === "dictation" || (await page.getByRole("button", { name: "Ouvir o ditado" }).isVisible().catch(() => false))) {
      if (!sawDictation) {
        await page.screenshot({ path: path.join(evidenceDir, "fr-b1-ditado.png"), fullPage: true });
      }
      sawDictation = true;
    }
    if (await page.getByText("Resposta incorreta").isVisible().catch(() => false)) sawWrong = true;
    if (await page.getByText("Correto.").isVisible().catch(() => false)) sawCorrect = true;
    if (
      pendingWrong &&
      signature === pendingWrong &&
      (await page.getByText(/mantém esta atividade/).isVisible().catch(() => false))
    ) {
      sawRetry = true;
      note("retry manteve a mesma atividade");
    }

    const correctBlock = page.locator("p", { hasText: "Resposta correta:" }).first();
    const revealed = (await correctBlock.isVisible().catch(() => false))
      ? ((await correctBlock.textContent()) ?? "").replace(/^.*Resposta correta:\s*/, "").trim()
      : "";

    const box = page.getByRole("textbox", { name: "Sua resposta" });
    const radios = page.getByRole("radio");
    const words = page.getByRole("group", { name: "Palavras disponíveis" });
    const willMiss = !revealed && ((await box.count()) > 0 || (await radios.count()) > 0 || (await words.count()) > 0);
    const hadIncorrect = await page.getByText("Resposta incorreta").isVisible().catch(() => false);
    if (await box.count()) {
      await box.fill(revealed || "zzz");
    } else if (await radios.count()) {
      const named = revealed ? page.getByRole("radio", { name: revealed }) : null;
      if (named && (await named.count())) await named.click();
      else await radios.last().click();
    } else if (await words.count()) {
      const buttons = words.getByRole("button");
      while ((await buttons.count()) > 0) await buttons.first().click();
    }

    const action = page.getByRole("button", { name: /Enviar tentativa|Continuar|Tentar novamente/ });
    await expect(action).toBeEnabled();
    const answered = page.waitForResponse(
      (response) =>
        response.url().includes("/vocabulary-cycle/answer") && response.request().method() === "POST",
      { timeout: 30_000 },
    );
    await action.click();
    await answered;
    await page.waitForFunction(
      ({ previous, hadIncorrect }) => {
        const done = [...document.querySelectorAll("h2")].some((node) =>
          node.textContent?.includes("Sessão concluída"),
        );
        if (done) return true;
        const region = document.querySelector("[data-interaction-family]");
        const next = region
          ? `${region.getAttribute("data-interaction-family")}|${(region.textContent ?? "").slice(0, 140)}`
          : "";
        const body = document.body.textContent ?? "";
        const incorrect = body.includes("Resposta incorreta");
        if (next && next !== previous) return true;
        return incorrect !== hadIncorrect;
      },
      { previous: signature, hadIncorrect },
      { timeout: 15_000 },
    );
    pendingWrong = willMiss ? signature : "";
    note(`passo ${step + 1}: família ${family ?? "sem"} revelado=${revealed || "-"}`);
  }

  await expect(page.getByRole("heading", { name: "Sessão concluída" })).toBeVisible();
  if (!sawDictation) {
    const longa = page.getByRole("button", { name: "Sessão longa" });
    if (await longa.isVisible()) {
      note("a dose curta não mostrou ditado; abrindo a sessão longa");
      await longa.click();
      for (let step = 0; step < 40; step += 1) {
        if (await page.getByRole("heading", { name: "Sessão concluída" }).isVisible()) break;
        if (await page.getByRole("button", { name: "Ouvir o ditado" }).isVisible().catch(() => false)) {
          sawDictation = true;
        }
        const box = page.getByRole("textbox", { name: "Sua resposta" });
        const radios = page.getByRole("radio");
        const words = page.getByRole("group", { name: "Palavras disponíveis" });
        if (await box.count()) await box.fill("Je suis d'accord avec cette idée.");
        else if (await radios.count()) await radios.first().click();
        else if (await words.count()) {
          const buttons = words.getByRole("button");
          while ((await buttons.count()) > 0) await buttons.first().click();
        }
        const action = page.getByRole("button", { name: /Enviar tentativa|Continuar|Tentar novamente/ });
        if (!(await action.isVisible())) break;
        if (!(await action.isEnabled())) break;
        await action.click();
        note(`longa ${step + 1}`);
        await page.waitForTimeout(200);
      }
    }
  }
  await expect(page.getByRole("heading", { name: "Sessão concluída" })).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "fr-b1-resumo.png"), fullPage: true });
  note(`famílias: ${[...families].join(", ")}`);
  note(`acerto=${sawCorrect} erro=${sawWrong} retry=${sawRetry} ditado=${sawDictation}`);
  fs.writeFileSync(path.join(evidenceDir, "fr-b1-session.log"), lines.join("\n"), "utf8");

  expect(sawWrong, "uma resposta errada deve aparecer").toBe(true);
  expect(sawRetry, "o retry deve manter a mesma atividade").toBe(true);
  expect(sawCorrect, "um acerto deve aparecer").toBe(true);
  expect(sawDictation, "a sessão deve incluir um ditado").toBe(true);
  expect(families.size).toBeGreaterThan(1);
});
