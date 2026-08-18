import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StudyModePage from "@/app/(app)/learn/[mode]/page";
import LearnPage from "@/app/(app)/learn/page";

const apiMock = vi.fn();
const notFound = vi.fn();
let currentMode = "vocabulary";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
  useParams: () => ({ mode: currentMode }),
  notFound: () => notFound(),
}));

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status = 400) {
      super(message);
      this.status = status;
    }
  },
}));

const profiles = { profiles: [{ language_code: "en", is_active: true }] };

const vocabularyLesson = {
  mode: "vocabulary",
  provider: "mock",
  language_code: "en",
  level: "B1",
  overall_level: "B1",
  skill: "vocabulary_grammar",
  skill_label: "Vocabulário e gramática",
  level_source: "placement_test",
  level_is_estimated: true,
  title: "Vocabulário essencial · B1",
  objective: "Ampliar vocabulário de alta frequência.",
  items: [
    {
      term: "to figure out",
      translation: "descobrir",
      example: "We need to figure out a solution.",
      example_translation: "Precisamos descobrir uma solução.",
      usage_note: "Chegar a uma resposta por reflexão.",
    },
    {
      term: "to come up with",
      translation: "bolar",
      example: "She came up with an idea.",
      example_translation: "Ela bolou uma ideia.",
      usage_note: "Criar algo novo.",
    },
  ],
};

function routeApi(handlers: Record<string, unknown>) {
  apiMock.mockImplementation((path: string) => {
    for (const [fragment, value] of Object.entries(handlers)) {
      if (path.startsWith(fragment)) {
        return value instanceof Error ? Promise.reject(value) : Promise.resolve(value);
      }
    }
    return Promise.reject(new Error(`sem handler: ${path}`));
  });
}

beforeEach(() => {
  apiMock.mockReset();
  notFound.mockReset();
  currentMode = "vocabulary";
});

describe("Lição adaptada ao nível", () => {
  it("mostra o nível e a origem vinda do teste de nivelamento", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": vocabularyLesson,
    });

    render(<StudyModePage />);

    expect(
      await screen.findByText(/Nível B1 · estimado pelo teste de nivelamento/),
    ).toBeInTheDocument();
    expect(screen.getByText("Vocabulário essencial · B1")).toBeInTheDocument();
  });

  it("pede a lição do modo e idioma corretos", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": vocabularyLesson,
    });

    render(<StudyModePage />);

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/lessons/generate", {
        method: "POST",
        body: { language_code: "en", mode: "vocabulary" },
      }),
    );
  });

  it("convida ao teste quando o nível não foi avaliado", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": {
        ...vocabularyLesson,
        level_source: "pending",
        level_is_estimated: false,
      },
    });

    render(<StudyModePage />);

    expect(await screen.findByText("Fazer teste de nível")).toBeInTheDocument();
    expect(screen.getByText(/padrão até você fazer o teste/)).toBeInTheDocument();
  });

  it("revela o significado só depois da tentativa", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": vocabularyLesson,
    });

    render(<StudyModePage />);

    expect(await screen.findByText("to figure out")).toBeInTheDocument();
    expect(screen.queryByText("descobrir")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Revelar significado" }));
    expect(await screen.findByText("descobrir")).toBeInTheDocument();
  });

  it("mostra erro recuperável quando a geração falha", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": new Error("falhou"),
    });

    render(<StudyModePage />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("marca conteúdo de demonstração quando vem do mock", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": vocabularyLesson,
    });

    render(<StudyModePage />);
    expect(await screen.findByText("Gerado em modo mock (IA local)")).toBeInTheDocument();
  });

  it("não marca demonstração quando vem da IA real", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": { ...vocabularyLesson, provider: "openrouter" },
    });

    render(<StudyModePage />);
    await screen.findByText("Vocabulário essencial · B1");
    expect(screen.queryByText("Gerado em modo mock (IA local)")).not.toBeInTheDocument();
  });

  it("conclui o vocabulário no último item ao clicar Eu sabia", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/v1/language-profiles")) return Promise.resolve(profiles);
      if (path.startsWith("/api/v1/lessons/generate")) return Promise.resolve(vocabularyLesson);
      if (path === "/api/v1/vocabulary") return Promise.resolve({ id: "v1" });
      return Promise.reject(new Error(`sem handler: ${path}`));
    });

    render(<StudyModePage />);
    await screen.findByText("to figure out");
    fireEvent.click(screen.getByRole("button", { name: "Revelar significado" }));
    fireEvent.click(screen.getByRole("button", { name: "Eu sabia · salvar" }));
    expect(await screen.findByText("to come up with")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Revelar significado" }));
    fireEvent.click(screen.getByRole("button", { name: "Eu sabia · concluir" }));
    expect(await screen.findByText("Vocabulário concluído")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para revisão" })).toHaveAttribute(
      "href",
      "/learn/review",
    );
  });

  it("aponta o diagnóstico para o teste de nivelamento", async () => {
    currentMode = "assessment";
    routeApi({ "/api/v1/language-profiles": profiles });

    render(<StudyModePage />);

    const link = await screen.findByRole("link", { name: /teste de nivelamento/ });
    expect(link).toHaveAttribute("href", "/placement-test");
  });

  it("rejeita um modo inexistente", () => {
    currentMode = "inexistente";
    routeApi({ "/api/v1/language-profiles": profiles });

    render(<StudyModePage />);
    expect(notFound).toHaveBeenCalled();
  });
});

describe("Lista de práticas", () => {
  const modesResponse = {
    language_code: "en",
    level: "B1",
    level_source: "placement_test",
    level_is_estimated: true,
    weakest_skills: [{ skill: "listening", label: "Compreensão auditiva" }],
    recommended_modes: ["listening", "writing"],
    modes: [],
  };

  it("prioriza os modos que atacam a competência mais fraca", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": modesResponse,
    });

    render(<LearnPage />);

    expect(await screen.findByText("Recomendado para você")).toBeInTheDocument();
    expect(
      screen.getByText(/Prioriza compreensão auditiva, sua competência mais fraca/),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Recomendado").length).toBeGreaterThan(0);
  });

  it("continua utilizável sem recomendação", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": new Error("indisponível"),
    });

    render(<LearnPage />);

    expect(await screen.findByText("Sugestão inicial")).toBeInTheDocument();
    expect(screen.getByText("O que vamos praticar?")).toBeInTheDocument();
  });

  it("recomenda o teste quando o nível não foi avaliado", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": {
        ...modesResponse,
        level_is_estimated: false,
        level_source: "pending",
        weakest_skills: [],
        recommended_modes: [],
      },
    });

    render(<LearnPage />);

    expect(
      await screen.findByText(/Faça o teste de nível para receber recomendações/),
    ).toBeInTheDocument();
  });
});

describe("Hub de Prática — seções", () => {
  const neutralModes = {
    language_code: "en",
    level: "B1",
    level_source: "placement_test",
    level_is_estimated: true,
    weakest_skills: [],
    recommended_modes: [],
    modes: [],
  };

  it("organiza os cards em três seções: Recomendado, Pratique uma habilidade e Avaliação", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": neutralModes,
    });

    render(<LearnPage />);
    await screen.findByText("O que vamos praticar?");

    expect(screen.getByRole("heading", { name: "Recomendado" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pratique uma habilidade" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Avaliação" })).toBeInTheDocument();
  });

  it("Recomendado contém Aula guiada e Revisão", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": neutralModes,
    });
    render(<LearnPage />);
    const heading = await screen.findByRole("heading", { name: "Recomendado" });
    const section = heading.closest("section") as HTMLElement;
    expect(within(section).getByRole("link", { name: /Aula guiada/ })).toHaveAttribute(
      "href",
      "/learn/guided",
    );
    expect(within(section).getByRole("link", { name: /Revisão/ })).toHaveAttribute(
      "href",
      "/learn/review",
    );
  });

  it("Pratique uma habilidade contém as sete habilidades, com Vocabulário e Conversação (voz)", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": neutralModes,
    });
    render(<LearnPage />);
    const heading = await screen.findByRole("heading", { name: "Pratique uma habilidade" });
    const section = heading.closest("section") as HTMLElement;
    const expected: Array<[RegExp, string]> = [
      [/Vocabulário/, "/learn/vocabulary"],
      [/Gramática/, "/learn/grammar"],
      [/Conversação/, "/learn/voice"],
      [/Pronúncia/, "/learn/pronunciation"],
      [/Compreensão auditiva/, "/learn/listening"],
      [/Leitura/, "/learn/reading"],
      [/Escrita/, "/learn/writing"],
    ];
    for (const [name, href] of expected) {
      expect(within(section).getByRole("link", { name })).toHaveAttribute("href", href);
    }
  });

  it("Avaliação contém só o Diagnóstico", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": neutralModes,
    });
    render(<LearnPage />);
    const heading = await screen.findByRole("heading", { name: "Avaliação" });
    const section = heading.closest("section") as HTMLElement;
    expect(within(section).getByRole("link", { name: /Diagnóstico/ })).toHaveAttribute(
      "href",
      "/learn/assessment",
    );
    expect(within(section).getAllByRole("link")).toHaveLength(1);
  });

  it("não existe mais 'Conversa por voz'; existe só um card 'Conversação'", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": neutralModes,
    });
    render(<LearnPage />);
    await screen.findByText("O que vamos praticar?");
    expect(screen.queryByText("Conversa por voz")).not.toBeInTheDocument();
    expect(screen.getAllByText("Conversação")).toHaveLength(1);
  });

  it("todos os cards do hub apontam para uma rota /learn/<slug> válida", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": neutralModes,
    });
    render(<LearnPage />);
    await screen.findByText("O que vamos praticar?");
    const expectedHrefs = [
      "/learn/guided",
      "/learn/review",
      "/learn/vocabulary",
      "/learn/grammar",
      "/learn/voice",
      "/learn/pronunciation",
      "/learn/listening",
      "/learn/reading",
      "/learn/writing",
      "/learn/assessment",
    ];
    for (const href of expectedHrefs) {
      const matches = screen.getAllByRole("link").filter((a) => a.getAttribute("href") === href);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    }
  });

  it("Gramática só mostra o selo Recomendado quando o backend recomenda, nunca de forma permanente", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": neutralModes, // recommended_modes: []
    });
    render(<LearnPage />);
    const heading = await screen.findByRole("heading", { name: "Pratique uma habilidade" });
    const section = heading.closest("section") as HTMLElement;
    const grammarCard = within(section).getByRole("link", { name: /Gramática/ });
    expect(within(grammarCard).queryByText("Recomendado")).not.toBeInTheDocument();
  });

  it("recomendação de 'conversation' do backend destaca e aponta para o card Conversação (slug voice)", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/modes": {
        ...neutralModes,
        weakest_skills: [{ skill: "speaking", label: "Fala" }],
        recommended_modes: ["conversation"],
      },
    });
    render(<LearnPage />);

    const hero = await screen.findByText("Recomendado para você");
    expect(hero.closest("a")).toHaveAttribute("href", "/learn/voice");

    const heading = await screen.findByRole("heading", { name: "Pratique uma habilidade" });
    const section = heading.closest("section") as HTMLElement;
    const conversationCard = within(section).getByRole("link", { name: /Conversação/ });
    expect(within(conversationCard).getByText("Recomendado")).toBeInTheDocument();
  });
});

describe("Conversação por voz", () => {
  const voiceLesson = {
    ...vocabularyLesson,
    mode: "voice",
    skill: "speaking",
    skill_label: "Fala",
    level: "A1",
    title: "Conversação",
    objective: "Praticar cumprimentos.",
    situation: "Apresentar-se a alguém que você acabou de conhecer",
    opening: "Good morning! How are you?",
    opening_translation: "Bom dia! Como você está?",
    suggested_replies: [],
    target_expressions: [],
  };

  beforeEach(() => {
    currentMode = "voice";
  });

  it("mostra a situação e um player de áudio, mas nunca o texto da fala do tutor", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": voiceLesson,
      "/api/v1/conversations": { id: "conv-1" },
    });

    render(<StudyModePage />);

    expect(
      await screen.findByText("Apresentar-se a alguém que você acabou de conhecer"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Good morning! How are you?")).not.toBeInTheDocument();
    expect(screen.queryByText("Bom dia! Como você está?")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reproduzir áudio" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar gravação" })).toBeInTheDocument();
  });

  it("ao transcrever a fala do aluno, avança o turno da conversa sem nunca mostrar a resposta do tutor em texto", async () => {
    class FakeMediaRecorder {
      mimeType = "audio/webm";
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      constructor(_stream: unknown, _options?: { mimeType?: string }) {}
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(["audio"], { type: "audio/webm" }) });
        this.onstop?.();
      }
      static isTypeSupported() {
        return true;
      }
    }
    Object.defineProperty(globalThis, "MediaRecorder", { writable: true, value: FakeMediaRecorder });
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] }),
      },
    });

    apiMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/v1/language-profiles")) return Promise.resolve(profiles);
      if (path.startsWith("/api/v1/lessons/generate")) return Promise.resolve(voiceLesson);
      if (path === "/api/v1/speech/transcribe") {
        return Promise.resolve({ text: "Good morning, I'm fine", provider: "groq" });
      }
      if (path === "/api/v1/conversations") return Promise.resolve({ id: "conv-1" });
      if (path === "/api/v1/conversations/conv-1/messages") {
        return Promise.resolve({ reply: "Nice to meet you. Where are you from?" });
      }
      return Promise.reject(new Error(`sem handler: ${path}`));
    });

    render(<StudyModePage />);
    await screen.findByRole("button", { name: "Iniciar gravação" });

    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/conversations/conv-1/messages", {
        method: "POST",
        body: { text: "Good morning, I'm fine" },
      }),
    );

    expect(await screen.findByText(/Você disse/)).toBeInTheDocument();
    expect(screen.queryByText("Nice to meet you. Where are you from?")).not.toBeInTheDocument();
  });
});

describe("Correção de escrita", () => {
  const writingLesson = {
    ...vocabularyLesson,
    mode: "writing",
    skill: "writing",
    skill_label: "Escrita",
    level: "A2",
    title: "Produção escrita · A2",
    objective: "Produzir um texto no seu nível.",
    prompt: "Descreva sua rotina diária.",
    min_words: 60,
    max_words: 110,
    rubric_hints: ["Sequência temporal clara"],
    useful_expressions: [],
  };

  const assessed = {
    id: "sub-1",
    status: "assessed",
    evaluated_by: "ai",
    normalized_score: 0.74,
    score: 0.74,
    target_level: "A2",
    estimated_level: "A2",
    word_count: 82,
    min_words: 60,
    max_words: 110,
    within_range: true,
    criteria: [
      { key: "gramatica", label: "Gramática", score: 0.7 },
      { key: "clareza", label: "Clareza", score: 0.9 },
    ],
    feedback: "Boa sequência temporal; atenção aos verbos no passado.",
  };

  beforeEach(() => {
    currentMode = "writing";
  });

  async function typeAndSubmit(text = "Um texto de rotina diária escrito pelo aluno.") {
    render(<StudyModePage />);
    const box = await screen.findByLabelText("Seu texto");
    fireEvent.change(box, { target: { value: text } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar para correção" }));
  }

  it("envia o texto com o nível e a faixa da tarefa", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": writingLesson,
      "/api/v1/writing": assessed,
    });

    await typeAndSubmit();

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/writing", {
        method: "POST",
        body: {
          language_code: "en",
          prompt: "Descreva sua rotina diária.",
          content_text: "Um texto de rotina diária escrito pelo aluno.",
          target_level: "A2",
          min_words: 60,
          max_words: 110,
        },
      }),
    );
  });

  it("mostra a devolutiva com pontuação e critérios", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": writingLesson,
      "/api/v1/writing": assessed,
    });

    await typeAndSubmit();

    expect(await screen.findByText("74%")).toBeInTheDocument();
    expect(screen.getByText("Gramática")).toBeInTheDocument();
    expect(screen.getByText("Clareza")).toBeInTheDocument();
    expect(
      screen.getByText("Boa sequência temporal; atenção aos verbos no passado."),
    ).toBeInTheDocument();
    expect(screen.getByText("Sustenta A2")).toBeInTheDocument();
  });

  it("avisa que a avaliação heurística não corrige gramática", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": writingLesson,
      "/api/v1/writing": {
        ...assessed,
        evaluated_by: "heuristic",
        criteria: [],
        feedback: undefined,
        metrics: { chars: 200, tokens: 40, sentences: 4, lexical_diversity: 0.72 },
      },
    });

    await typeAndSubmit();

    expect(await screen.findByText(/não corrige gramática/)).toBeInTheDocument();
    expect(screen.getByText("O que foi medido")).toBeInTheDocument();
  });

  it("sinaliza texto fora da faixa pedida", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": writingLesson,
      "/api/v1/writing": { ...assessed, within_range: false, word_count: 12 },
    });

    await typeAndSubmit();

    expect(await screen.findByText(/fora da faixa de 60–110/)).toBeInTheDocument();
  });

  it("mostra erro quando a correção falha", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": writingLesson,
      "/api/v1/writing": new Error("indisponível"),
    });

    await typeAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível enviar o texto para correção.",
    );
  });
});

describe("Conversação calibrada pelo nível", () => {
  const conversationLesson = {
    ...vocabularyLesson,
    mode: "conversation",
    skill: "speaking",
    skill_label: "Fala",
    level: "A1",
    title: "Conversação · A1",
    objective: "Praticar cumprimentos.",
    situation: "Apresentar-se a alguém que você acabou de conhecer",
    opening: "Good morning! How are you?",
    opening_translation: "Bom dia! Como você está?",
    suggested_replies: [],
    target_expressions: ["good morning", "my name is"],
  };

  const turn = {
    reply: "Nice to meet you. Where are you from?",
    reply_translation: "Prazer em conhecer. De onde você é?",
    corrections: [
      {
        original: "I is Ana",
        corrected: "I am Ana",
        explanation: "Com 'I' o verbo to be é 'am'.",
      },
    ],
    suggestions: ["my name is"],
    corrections_available: true,
    provider: "openrouter",
    level: "A1",
  };

  beforeEach(() => {
    currentMode = "conversation";
  });

  async function chat(response: unknown) {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": conversationLesson,
      "/api/v1/conversations": response,
    });
    render(<StudyModePage />);
    await screen.findByText("Good morning! How are you?");
    const box = screen.getByPlaceholderText("Escreva sua resposta…");
    fireEvent.change(box, { target: { value: "I is Ana" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
  }

  it("abre a conversa com a situação da lição, não um tópico fixo", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": conversationLesson,
      "/api/v1/conversations": { id: "conv-1" },
    });

    render(<StudyModePage />);

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/conversations", {
        method: "POST",
        body: {
          language_code: "en",
          topic: "Apresentar-se a alguém que você acabou de conhecer",
          opening: "Good morning! How are you?",
        },
      }),
    );
  });

  it("mostra tradução da abertura em nível baixo", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": conversationLesson,
      "/api/v1/conversations": { id: "conv-1" },
    });

    render(<StudyModePage />);
    expect(await screen.findByText("Bom dia! Como você está?")).toBeInTheDocument();
  });

  it("omite tradução quando o nível não precisa", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": {
        ...conversationLesson,
        level: "B2",
        opening_translation: null,
      },
      "/api/v1/conversations": { id: "conv-1" },
    });

    render(<StudyModePage />);
    await screen.findByText("Good morning! How are you?");
    expect(screen.queryByText("Bom dia! Como você está?")).not.toBeInTheDocument();
  });

  it("exibe a correção do tutor ancorada na fala do aluno", async () => {
    await chat(turn);

    expect(await screen.findByText("I am Ana")).toBeInTheDocument();
    expect(screen.getByText("Com 'I' o verbo to be é 'am'.")).toBeInTheDocument();
    expect(screen.getByText("Nice to meet you. Where are you from?")).toBeInTheDocument();
  });

  it("avisa quando o modo mock não corrige", async () => {
    await chat({
      ...turn,
      corrections: [],
      corrections_available: false,
      provider: "mock",
    });

    expect(await screen.findByText(/não corrige o que você escreve/)).toBeInTheDocument();
  });

  it("não marca demonstração quando a IA real responde", async () => {
    await chat(turn);
    await screen.findByText("Nice to meet you. Where are you from?");
    expect(screen.queryByText(/Modo demonstração/)).not.toBeInTheDocument();
  });

  it("mostra erro sem inventar resposta do tutor", async () => {
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": conversationLesson,
      "/api/v1/conversations": new Error("fora do ar"),
    });
    render(<StudyModePage />);
    await screen.findByText("Good morning! How are you?");
    fireEvent.change(screen.getByPlaceholderText("Escreva sua resposta…"), {
      target: { value: "hello" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível obter resposta do tutor.",
    );
  });
});

describe("Persistência da abertura", () => {
  it("envia a abertura para o backend não repeti-la no primeiro turno", async () => {
    currentMode = "conversation";
    routeApi({
      "/api/v1/language-profiles": profiles,
      "/api/v1/lessons/generate": {
        ...vocabularyLesson,
        mode: "conversation",
        skill: "speaking",
        level: "B2",
        title: "Conversação · B2",
        situation: "Discordar educadamente",
        opening: "The policy brought about significant change.",
        opening_translation: null,
        suggested_replies: [],
        target_expressions: [],
      },
      "/api/v1/conversations": { id: "conv-1" },
    });

    render(<StudyModePage />);

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/conversations", {
        method: "POST",
        body: {
          language_code: "en",
          topic: "Discordar educadamente",
          opening: "The policy brought about significant change.",
        },
      }),
    );
  });
});
