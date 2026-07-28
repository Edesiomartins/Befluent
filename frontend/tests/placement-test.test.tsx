import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PlacementTestIntroPage from "@/app/(app)/placement-test/page";
import PlacementTestRunnerPage from "@/app/(app)/placement-test/[id]/page";
import PlacementResultPage from "@/app/(app)/placement-test/[id]/resultado/page";

const replace = vi.fn();
const push = vi.fn();
const apiMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push, refresh: vi.fn() }),
  useParams: () => ({ id: "test-1" }),
}));

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status = 400, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

const progress = {
  answered: 3,
  minimum: 12,
  target: 20,
  maximum: 30,
  writing_submitted: false,
};

const objectiveItem = {
  id: "item-1",
  skill: "vocabulary_grammar",
  skill_label: "Vocabulário e gramática",
  item_type: "multiple_choice",
  prompt: "Qual é a saudação usada pela manhã?",
  instructions: null,
  passage: null,
  options: ["Good morning", "Good night", "Goodbye", "See you"],
  audio_url: null,
  audio_script: null,
};

function mockRoute(handler: (path: string, options?: { method?: string }) => unknown) {
  apiMock.mockImplementation((path: string, options?: { method?: string }) =>
    Promise.resolve(handler(path, options)),
  );
}

beforeEach(() => {
  replace.mockReset();
  push.mockReset();
  apiMock.mockReset();
});

describe("Tela inicial do teste", () => {
  it("explica o teste e avisa que não é certificação", async () => {
    mockRoute(() => ({ test: null }));
    render(<PlacementTestIntroPage />);

    expect(screen.getByText("Descubra seu nível atual")).toBeInTheDocument();
    expect(screen.getByText(/nível estimado/)).toBeInTheDocument();
    expect(screen.getByText(/não uma certificação oficial/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar teste" })).toBeInTheDocument();
  });

  it("avisa sobre fones e possibilidade de retomar", async () => {
    mockRoute(() => ({ test: null }));
    render(<PlacementTestIntroPage />);

    expect(screen.getByText(/fones de ouvido/)).toBeInTheDocument();
    expect(screen.getByText(/sair e retomar/)).toBeInTheDocument();
  });

  it("inicia o teste e navega para a execução", async () => {
    mockRoute((path) => (path.includes("current") ? { test: null } : { id: "novo-teste" }));
    render(<PlacementTestIntroPage />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar teste" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/placement-test/novo-teste"));
  });

  it("oferece retomar teste em andamento", async () => {
    mockRoute(() => ({
      test: { id: "test-1", progress: { ...progress, answered: 5 } },
    }));
    render(<PlacementTestIntroPage />);

    expect(await screen.findByText("Você tem um teste em andamento")).toBeInTheDocument();
    expect(screen.getByText(/5 de 20 atividades/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retomar teste" })).toHaveAttribute(
      "href",
      "/placement-test/test-1",
    );
  });

  it("mostra erro real quando não consegue iniciar", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string) =>
      path.includes("current")
        ? Promise.resolve({ test: null })
        : Promise.reject(new ApiError("Você poderá refazer o teste em 30 dias.", 409)),
    );
    render(<PlacementTestIntroPage />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar teste" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Você poderá refazer o teste em 30 dias.",
    );
    expect(push).not.toHaveBeenCalled();
  });
});

describe("Execução do teste", () => {
  it("mostra questão objetiva com progresso acessível", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: objectiveItem, stage: "objective", progress }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    expect(await screen.findByText(objectiveItem.prompt)).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "15");
    expect(screen.getByText("Vocabulário e gramática")).toBeInTheDocument();
  });

  it("não revela o nível da questão nem a resposta correta", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: objectiveItem, stage: "objective", progress }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);
    await screen.findByText(objectiveItem.prompt);

    expect(screen.queryByText(/A1|A2|B1|B2/)).not.toBeInTheDocument();
    expect(screen.queryByText(/correta/i)).not.toBeInTheDocument();
  });

  it("exige seleção antes de continuar", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: objectiveItem, stage: "objective", progress }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);
    await screen.findByText(objectiveItem.prompt);

    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: "Good morning" }));
    expect(screen.getByRole("button", { name: "Continuar" })).toBeEnabled();
  });

  it("envia a resposta com tempo de resposta", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: objectiveItem, stage: "objective", progress }
        : path.includes("/answers")
          ? { accepted: true, progress }
          : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);
    await screen.findByText(objectiveItem.prompt);

    fireEvent.click(screen.getByRole("radio", { name: "Good morning" }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/placement-tests/test-1/answers",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ item_id: "item-1", answer: "Good morning" }),
        }),
      ),
    );
  });

  it("mostra atividade de escuta com botão de áudio", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? {
            item: {
              ...objectiveItem,
              skill: "listening",
              skill_label: "Compreensão auditiva",
              audio_script: "I would like a coffee.",
            },
            stage: "objective",
            progress,
          }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    expect(await screen.findByRole("button", { name: "Ouvir áudio" })).toBeInTheDocument();
  });

  it("mostra a etapa de escrita com contador", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? {
            item: {
              ...objectiveItem,
              skill: "writing",
              skill_label: "Escrita",
              item_type: "short_writing",
              prompt: "Escreva de 3 a 5 frases se apresentando.",
              options: [],
            },
            stage: "writing",
            progress,
          }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    const textarea = await screen.findByLabelText("Sua resposta");
    fireEvent.change(textarea, { target: { value: "My name is Ana." } });
    expect(screen.getByText("15 caracteres")).toBeInTheDocument();
  });

  it("conclui o teste e vai para o resultado", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: null, stage: "ready_to_complete", progress }
        : path.includes("/complete")
          ? { id: "test-1", status: "completed" }
          : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Ver meu resultado" }));

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/placement-test/test-1/resultado"),
    );
  });

  it("mostra erro recuperável quando a API falha", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string) =>
      path.includes("next-item")
        ? Promise.reject(new ApiError("Falha ao carregar atividade.", 500))
        : Promise.resolve({ language_code: "en" }),
    );

    render(<PlacementTestRunnerPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha ao carregar atividade.");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});

describe("Resultado", () => {
  const result = {
    id: "test-1",
    language_code: "en",
    status: "completed",
    completed_at: "2026-07-27T12:00:00+00:00",
    duration_seconds: 900,
    overall_level: "B1",
    overall: {
      code: "B1",
      name_pt: "B1 — Intermediário",
      short_description: "Mantém conversas sobre temas familiares.",
      order_index: 3,
      testable: true,
    },
    confidence_score: 68,
    confidence_label: "moderada",
    items_answered: 20,
    weights_used: { reading: 0.25 },
    recommendations: [
      { skill: "writing", reason: "below_overall", priority: 1 },
      { skill: "speaking", reason: "not_assessed", priority: 2 },
    ],
    skills: [
      { skill: "reading", label: "Leitura", estimated_level: "B2", level: null, score: 4, max_score: 4, status: "assessed" },
      { skill: "writing", label: "Escrita", estimated_level: "A2", level: null, score: 1, max_score: 4, status: "assessed" },
      { skill: "speaking", label: "Fala", estimated_level: null, level: null, score: 0, max_score: 0, status: "not_available" },
    ],
    speaking_available: false,
    disclaimer: "Nível estimado. Não é uma certificação oficial.",
  };

  it("exibe nível geral, confiança e ressalva", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    expect(await screen.findByText("Seu nível estimado")).toBeInTheDocument();
    expect(screen.getByText("B1")).toBeInTheDocument();
    expect(screen.getByText(/moderada \(68\/100\)/)).toBeInTheDocument();
    expect(
      screen.getByText("Nível estimado. Não é uma certificação oficial."),
    ).toBeInTheDocument();
  });

  it("lista competências avaliadas e não avaliadas", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    // Rótulos se repetem entre a lista de competências e o bloco de prioridades.
    expect(await screen.findAllByText("Leitura")).not.toHaveLength(0);
    expect(screen.getAllByText("Escrita")).not.toHaveLength(0);
    expect(screen.getAllByText("Fala")).not.toHaveLength(0);
    expect(screen.getByText("não avaliada")).toBeInTheDocument();
    expect(screen.getByText(/avaliação de fala ainda não está disponível/)).toBeInTheDocument();
  });

  it("mostra prioridades de estudo", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    expect(await screen.findByText("Pontos fortes e prioridades")).toBeInTheDocument();
    expect(screen.getByText(/abaixo do nível geral/)).toBeInTheDocument();
  });

  it("oferece caminhos após o resultado", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    expect(await screen.findByRole("link", { name: "Ir para o dashboard" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: "Começar a praticar" })).toBeInTheDocument();
  });

  it("com competências empatadas não aponta forte e fraco iguais", async () => {
    mockRoute(() => ({
      ...result,
      skills: [
        { skill: "reading", label: "Leitura", estimated_level: "B2", level: null, score: 4, max_score: 4, status: "assessed" },
        { skill: "listening", label: "Compreensão auditiva", estimated_level: "B2", level: null, score: 4, max_score: 4, status: "assessed" },
      ],
      recommendations: [],
    }));
    render(<PlacementResultPage />);

    expect(
      await screen.findByText("Seu desempenho ficou equilibrado entre as competências avaliadas."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Ponto forte")).not.toBeInTheDocument();
  });

  it("mostra erro quando o resultado não carrega", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Este teste ainda não foi concluído.", 409));
    render(<PlacementResultPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Este teste ainda não foi concluído.",
    );
  });
});
