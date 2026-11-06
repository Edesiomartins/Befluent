import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { expect, test, type Response } from "@playwright/test";

const evidenceDir = path.resolve(__dirname, "../../docs/stage-1-reference/evidence");
const api = "http://127.0.0.1:8011";

const PRIVATE_KEYS = new Set([
  "answer",
  "audio_text",
  "canonical_answer",
  "content",
  "corrections",
  "email",
  "example",
  "example_sentence",
  "example_translation",
  "example_translation_pt",
  "explanation",
  "opening",
  "opening_translation",
  "options",
  "password",
  "prompt",
  "prompt_native",
  "prompt_pt",
  "prompt_target",
  "reply",
  "reply_translation",
  "scenario_native",
  "scenario_target",
  "selected_answer",
  "situation",
  "situation_native",
  "student_response",
  "suggestions",
  "term",
  "text",
  "token",
  "topic",
  "translation",
  "translation_pt",
]);

function redact(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== "object") return value;
  const output: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (PRIVATE_KEYS.has(key)) continue;
    output[key] = redact(item);
  }
  return output;
}

function headSha(): string {
  try {
    return execSync("git rev-parse HEAD", {
      cwd: path.resolve(__dirname, "../.."),
      encoding: "utf8",
    }).trim();
  } catch {
    return "não determinado";
  }
}

test("FR B1 pt-BR: a mesma conta em desktop e mobile", async ({ page }) => {
  test.setTimeout(360_000);
  fs.mkdirSync(evidenceDir, { recursive: true });
  const lines: string[] = [];
  const traces: unknown[] = [];
  const note = (line: string) => {
    lines.push(line);
    console.log(line);
    fs.appendFileSync(path.join(evidenceDir, "session.log"), `${line}\n`, "utf8");
  };
  fs.writeFileSync(path.join(evidenceDir, "session.log"), "", "utf8");
  const keep = async (label: string, response: Response) => {
    const contentType = response.headers()["content-type"] || "";
    if (!contentType.includes("json")) {
      traces.push({
        label,
        url: response.url().replace(api, ""),
        status: response.status(),
        content_type: contentType,
        body: "omitido: não é JSON de diagnóstico",
      });
      return null;
    }
    const body = redact(await response.json());
    traces.push({ label, url: response.url().replace(api, ""), status: response.status(), body });
    return body as Record<string, unknown>;
  };

  let failure: unknown = null;
  const checks = {
    desktop_text: false,
    desktop_voice_ui: false,
    desktop_stt_stub: false,
    desktop_tts_stub: false,
    desktop_vocabulary: false,
    desktop_error: false,
    desktop_retry_or_defer: false,
    mobile_resume_same_flow: false,
    mobile_text_same_account: false,
    exhaustion: "não observado",
    stt_microphone: "PENDENTE — microfone real não foi usado",
    tts_human_listening: "PENDENTE — áudio real não foi ouvido por uma pessoa",
  };
  let desktopFlowId = "";
  let mobileFlowId = "";

  try {
    await page.setViewportSize({ width: 1280, height: 800 });
    const email = `fr-b1-${Date.now()}@example.com`;
    const password = "Senha12345";
    await page.goto("/register");
    await page.getByLabel("Nome").fill("Aluno FR");
    await page.getByLabel("E-mail").fill(email);
    await page.getByRole("textbox", { name: "Senha", exact: true }).fill(password);
    await page.getByLabel("Confirmar senha").fill(password);
    await page.getByRole("button", { name: "Criar minha conta" }).click();
    await page.waitForURL(/\/login/);
    await page.getByLabel("E-mail").fill(email);
    await page.getByRole("textbox", { name: "Senha", exact: true }).fill(password);
    await page.getByRole("button", { name: "Entrar" }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/);
    if (!page.url().includes("/onboarding")) await page.goto("/onboarding");
    const nativeHeading = page.getByRole("heading", { name: "Qual é sua língua nativa?" });
    const languageHeading = page.getByRole("heading", { name: "Qual idioma você quer estudar?" });
    const nativeShown = await nativeHeading
      .waitFor({ state: "visible", timeout: 20_000 })
      .then(() => true)
      .catch(() => false);
    if (nativeShown) {
      const nativeSelect = page.locator("#onboarding-native-language");
      await expect(nativeSelect.locator("option[value='pt-BR']")).toHaveCount(1);
      await nativeSelect.selectOption("pt-BR");
      await page.getByRole("button", { name: "Continuar" }).click();
      note("língua nativa pt-BR");
    } else {
      note("o onboarding não pediu língua nativa antes do idioma");
    }
    await languageHeading.waitFor();
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
    note("plano FR B1 pt-BR criado; a conta não entra nos artefatos");

    const started = page.waitForResponse(
      (response) => response.url().includes("/api/v1/conversations") && response.request().method() === "POST",
    );
    await page.goto("/learn/conversation");
    const startBody = await keep("desktop-conversa-inicio", await started);
    const openedConversationId = String(startBody?.id || "");
    note(`conversa texto id=${openedConversationId || "ausente"} provider ainda não chamado`);
    await page.getByLabel("Sua resposta").waitFor({ timeout: 60_000 });
    await page.getByLabel("Sua resposta").fill("Je voudrais un billet.");
    const sent = page.waitForResponse(
      (response) => response.url().includes("/messages") && response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Enviar" }).click();
    const turn = await keep("desktop-conversa-turno", await sent);
    const turnTrace = (turn?.selection_trace || {}) as Record<string, unknown>;
    const conversationId = String(turnTrace.conversation_id || openedConversationId);
    checks.desktop_text = Boolean(conversationId) && turn?.provider === "mock";
    if (openedConversationId && conversationId && openedConversationId !== conversationId) {
      note(`INCIDENTE: abertura ${openedConversationId} difere do turno ${conversationId}`);
    }
    note(`turno texto id=${conversationId || "ausente"} provider=${String(turn?.provider || "ausente")} model=${String(turn?.model ?? "null")} alvo=${String(turn?.target_language || "ausente")} nativo=${String(turn?.native_language || "ausente")}`);
    await page.screenshot({ path: path.join(evidenceDir, "desktop-conversa-texto.png"), fullPage: true });

    await page.goto("/learn/voice");
    await page.getByText("Situação", { exact: true }).waitFor({ timeout: 30_000 });
    checks.desktop_voice_ui = true;
    const heard = page.getByRole("button", { name: /Ouvir|Reproduzir áudio/ }).first();
    if (await heard.isVisible()) {
      const synth = page.waitForResponse(
        (response) => response.url().includes("/speech/synthesize"),
        { timeout: 15_000 },
      ).catch(() => null);
      await heard.click();
      const synthResponse = await synth;
      if (synthResponse) {
        checks.desktop_tts_stub = synthResponse.ok();
        traces.push({
          label: "desktop-tts-stub",
          url: "/api/v1/speech/synthesize",
          status: synthResponse.status(),
          content_type: synthResponse.headers()["content-type"] || "",
          provider_esperado: "mock",
          validacao_humana_audio: "PENDENTE",
        });
        note(`TTS stub status=${synthResponse.status()} type=${synthResponse.headers()["content-type"] || "ausente"}; audição humana PENDENTE`);
      } else {
        note("o botão Ouvir não chamou /speech/synthesize neste clique");
      }
    }
    const record = page.getByRole("button", { name: "Iniciar gravação" });
    if (await record.isVisible().catch(() => false)) {
      const transcribe = page.waitForResponse(
        (response) => response.url().includes("/speech/transcribe"),
        { timeout: 20_000 },
      ).catch(() => null);
      await record.click({ timeout: 5_000 });
      await page.waitForTimeout(1200);
      const stop = page.getByRole("button", { name: "Parar gravação" });
      if (await stop.isVisible().catch(() => false)) await stop.click();
      const sttResponse = await transcribe;
      if (sttResponse) {
        const sttBody = await keep("desktop-stt-stub", sttResponse);
        checks.desktop_stt_stub = sttBody?.provider === "mock";
        note("STT exercitado com dispositivo falso e provedor mock; transcrição não foi salva; fala humana PENDENTE");
      } else {
        note("gravação stub não chamou /speech/transcribe");
      }
    } else {
      note("botão de gravação ausente; STT não exercitado");
    }
    await page.screenshot({ path: path.join(evidenceDir, "desktop-conversa-voz.png"), fullPage: true });
    note("microfone físico não foi usado");

    const cycleWait = page.waitForResponse(
      (response) => response.url().includes("/vocabulary-cycle") && response.ok(),
      { timeout: 90_000 },
    );
    await page.goto("/learn/vocabulary");
    const cycle = await keep("desktop-vocabulario", await cycleWait);
    const flow = (cycle?.flow || {}) as Record<string, unknown>;
    desktopFlowId = String(flow.id || "");
    const lessonId = String(cycle?.lesson_id || "");
    checks.desktop_vocabulary = Boolean(desktopFlowId);
    const selection = (cycle?.selection_trace || {}) as Record<string, unknown>;
    const exhaustion = selection.exhaustion as Record<string, unknown> | null;
    if (exhaustion && (exhaustion.aggregate_reason || exhaustion.reason)) {
      checks.exhaustion = String(exhaustion.aggregate_reason || exhaustion.reason);
    }
    note(`fluxo desktop=${desktopFlowId || "ausente"} cursor=${String(flow.activity_cursor ?? "ausente")} esgotamento=${checks.exhaustion}`);
    await page.screenshot({ path: path.join(evidenceDir, "desktop-vocabulario.png"), fullPage: true });

    for (let step = 0; step < 14 && !checks.desktop_retry_or_defer; step += 1) {
      const activity = page.locator("[data-interaction-family]").first();
      if (!(await activity.isVisible().catch(() => false))) break;
      const box = page.getByRole("textbox", { name: "Sua resposta" });
      const radios = page.getByRole("radio");
      const words = page.getByRole("group", { name: "Palavras disponíveis" });
      if (await box.count()) await box.fill("zzz");
      else if (await radios.count()) await radios.last().click();
      else if (await words.count()) {
        while ((await words.getByRole("button").count()) > 0) {
          await words.getByRole("button").last().click();
        }
      }
      const action = page.getByRole("button", { name: /Verificar|Enviar tentativa|Continuar|Tentar novamente/ });
      if (!(await action.isVisible().catch(() => false))) break;
      if (!(await action.isEnabled())) {
        note(`passo ${step + 1} ação desabilitada`);
        break;
      }
      const answered = page.waitForResponse(
        (response) => response.url().includes("/vocabulary-cycle/answer") && response.request().method() === "POST",
        { timeout: 20_000 },
      );
      await action.click();
      const answerResponse = await answered.catch(() => null);
      if (!answerResponse) {
        note(`passo ${step + 1} sem POST de resposta`);
        break;
      }
      const answerBody = await keep(`desktop-resposta-${step + 1}`, answerResponse);
      const answerTrace = ((answerBody?.selection_trace || {}) as Record<string, unknown>).latest
        ? ((answerBody?.selection_trace as Record<string, unknown>).latest as Record<string, unknown>)
        : ((answerBody?.selection_trace || {}) as Record<string, unknown>);
      const reason = String(answerTrace.reason || "");
      if (["lexical_family_retired", "interaction_change_retry", "same_activity_retry", "activities_exhausted"].includes(reason)) {
        checks.desktop_error = true;
        checks.desktop_retry_or_defer = true;
      }
      note(`passo ${step + 1} status=${answerResponse.status()} reason=${reason || "ausente"}`);
      if (checks.desktop_retry_or_defer) break;
    }
    await page.screenshot({ path: path.join(evidenceDir, "desktop-vocabulario-erro.png"), fullPage: true });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(evidenceDir, "mobile-vocabulario-mesma-tela.png"), fullPage: true });
    if (lessonId) {
      const resumed = await page.request.get(`${api}/api/v1/lessons/${lessonId}/vocabulary-cycle`);
      let resumeBody: Record<string, unknown> | null = null;
      if (resumed.headers()["content-type"]?.includes("json")) {
        resumeBody = redact(await resumed.json()) as Record<string, unknown>;
      }
      traces.push({
        label: "mobile-retomada-api",
        url: `/api/v1/lessons/${lessonId}/vocabulary-cycle`,
        status: resumed.status(),
        body: resumeBody,
      });
      const resumeFlow = (resumeBody?.flow || {}) as Record<string, unknown>;
      mobileFlowId = String(resumeFlow.id || "");
      note(`GET da mesma lição status=${resumed.status()} fluxo=${mobileFlowId || "ausente"}`);
    }
    checks.mobile_resume_same_flow = Boolean(desktopFlowId) && desktopFlowId === mobileFlowId;
    note(`retomada mobile mesmo fluxo=${checks.mobile_resume_same_flow}; o hub /learn/vocabulary gera lição nova e não foi usado como segunda jornada`);
    await page.screenshot({ path: path.join(evidenceDir, "mobile-vocabulario-retomada.png"), fullPage: true });

    const mobileStarted = page.waitForResponse(
      (response) => response.url().includes("/api/v1/conversations") && response.request().method() === "POST" && !response.url().includes("/messages"),
      { timeout: 30_000 },
    );
    await page.goto("/learn/conversation");
    const mobileStart = await keep("mobile-conversa-inicio", await mobileStarted);
    checks.mobile_text_same_account = Boolean(mobileStart?.id);
    note(`conversa mobile id=${String(mobileStart?.id || "ausente")}; a UI inicia outra conversa, a anterior permanece ${conversationId || "ausente"}`);
    if (conversationId) {
      const history = await page.request.get(`${api}/api/v1/conversations/${conversationId}/messages`);
      traces.push({
        label: "retomada-conversa-original",
        status: history.status(),
        conversation_id: conversationId,
        mesma_conta: history.ok(),
        corpo: "omitido: contém texto da conversa",
      });
      note(`GET da conversa original status=${history.status()}`);
    }
    await page.screenshot({ path: path.join(evidenceDir, "mobile-conversa-texto.png"), fullPage: true });

    expect(checks.desktop_text, "conversa por texto no desktop").toBe(true);
    expect(checks.desktop_voice_ui, "tela de voz").toBe(true);
    expect(checks.desktop_vocabulary, "ciclo de vocabulário").toBe(true);
    expect(checks.desktop_retry_or_defer, "erro com retry ou adiamento").toBe(true);
    expect(checks.mobile_resume_same_flow, "a retomada mobile usa o mesmo fluxo").toBe(true);
  } catch (error) {
    failure = error;
    note(`interrompido: ${error instanceof Error ? error.message : String(error)}`);
    await page.screenshot({ path: path.join(evidenceDir, "falha.png"), fullPage: true }).catch(() => undefined);
  } finally {
    const manifest = {
      head: headSha(),
      date: new Date().toISOString(),
      environment: "local",
      database: "sqlite backend/tmp/e2e-fr-b1.sqlite3",
      viewports: ["desktop 1280x800", "mobile 390x844"],
      same_account: true,
      desktop_flow_id: desktopFlowId || null,
      mobile_flow_id: mobileFlowId || null,
      commands: [
        "frontend: npx playwright test e2e/fr-b1-session.spec.ts",
      ],
      providers: {
        ai: "mock",
        stt: "mock com dispositivo falso do Chromium, se /speech/transcribe foi chamado; microfone físico e fala humana PENDENTES",
        tts: "mock se /speech/synthesize foi chamado; audição humana PENDENTE",
      },
      checks,
      result: failure ? "falhou" : "concluiu",
    };
    fs.writeFileSync(path.join(evidenceDir, "traces.json"), JSON.stringify(traces, null, 2), "utf8");
    fs.writeFileSync(path.join(evidenceDir, "manifest.json"), JSON.stringify(manifest, null, 2), "utf8");
    fs.writeFileSync(path.join(evidenceDir, "session.log"), lines.join("\n"), "utf8");
  }
  if (failure) throw failure;
});
