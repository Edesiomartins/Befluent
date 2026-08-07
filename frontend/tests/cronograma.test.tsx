import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CronogramaPage from "@/app/(app)/cronograma/page";
import CurriculumDayPage from "@/app/(app)/cronograma/dia/[id]/page";
import { ApiError } from "@/lib/api";

const apiMock = vi.fn();
const push = vi.fn();
let dayId = "day-1";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push, refresh: vi.fn() }),
  useParams: () => ({ id: dayId }),
  usePathname: () => "/cronograma",
  notFound: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  // A classe vive dentro do factory: `vi.mock` é hoisted para o topo do arquivo
  // e não enxerga nada declarado depois dele.
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status = 400, code?: string) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code;
    }
  },
}));

const profiles = { profiles: [{ language_code: "en", is_active: true }] };

const block = (id: string, skill: string, label: string, extra = {}) => ({
  id,
  skill,
  skill_label: label,
  mode: skill,
  position: 1,
  estimated_minutes: 10,
  cefr_level: "A2",
  topic: `Apresentações e rotina — ${label.toLowerCase()}`,
  lesson_ref: null,
  status: "pending",
  score: null,
  ...extra,
});

const day = {
  id: "day-1",
  day_number: 1,
  scheduled_date: "2026-08-03",
  status: "pending",
  completed_at: null,
  total_minutes: 52,
  blocks_total: 3,
  blocks_completed: 0,
  blocks: [
    block("b-1", "vocabulary", "Vocabulário"),
    block("b-2", "grammar", "Gramática"),
    block("b-3", "review", "Revisão"),
  ],
};

const week = {
  id: "w-1",
  week_number: 1,
  theme: "Apresentações e rotina",
  cefr_focus: "A2",
  is_checkpoint: false,
};

const progress = {
  days_total: 90,
  days_completed: 4,
  percent_complete: 4.4,
  current_day_number: 5,
  overdue_days: 0,
  needs_reschedule: false,
  next_checkpoint_week: 2,
};

const curriculum = {
  id: "cur-1",
  duration_days: 90,
  start_date: "2026-08-03",
  entry_level: "A2",
  target_level: "B2",
  entry: { code: "A2", name_pt: "A2 — Básico", short_description: "", order_index: 2, testable: true },
  target: { code: "B2", name_pt: "B2", short_description: "", order_index: 4, testable: true },
  status: "active",
  generated_from: "placement",
  weeks_total: 13,
  disclaimer: "Cronograma estimado a partir do teste de nivelamento.",
  progress,
};

const activeCurriculum = {
  ...curriculum,
  weeks: [
    week,
    { id: "w-2", week_number: 2, theme: "Família e pessoas próximas", cefr_focus: "A2", is_checkpoint: true },
    { id: "w-3", week_number: 3, theme: "Comida e restaurante", cefr_focus: "A2", is_checkpoint: false },
  ],
};

const today = { curriculum, week, day, overdue_days: [] };

function routeApi(handlers: Array<[string, unknown]>) {
  apiMock.mockImplementation((path: string) => {
    for (const [fragment, value] of handlers) {
      if (path.startsWith(fragment)) {
        return value instanceof Error ? Promise.reject(value) : Promise.resolve(value);
      }
    }
    return Promise.reject(new Error(`sem handler: ${path}`));
  });
}

beforeEach(() => {
  apiMock.mockReset();
  push.mockReset();
  dayId = "day-1";
});

describe("Página do cronograma", () => {
  it("mostra o progresso geral com a meta de nível", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", activeCurriculum],
      ["/api/v1/curriculum/day/today", today],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByText("Dia 5 de 90")).toBeInTheDocument();
    expect(screen.getByText("A2 → B2")).toBeInTheDocument();
    expect(screen.getByText(/4 dias concluídos/)).toBeInTheDocument();
    expect(screen.getByText("Próximo checkpoint: semana 2")).toBeInTheDocument();
  });

  it("declara que o cronograma é estimativa, não garantia", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", activeCurriculum],
      ["/api/v1/curriculum/day/today", today],
    ]);

    render(<CronogramaPage />);
    expect(
      await screen.findByText(/Cronograma estimado a partir do teste de nivelamento/),
    ).toBeInTheDocument();
  });

  it("lista as semanas com tema e marca o checkpoint", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", activeCurriculum],
      ["/api/v1/curriculum/day/today", today],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByText("Família e pessoas próximas")).toBeInTheDocument();
    expect(screen.getByText("Comida e restaurante")).toBeInTheDocument();
    expect(screen.getAllByText("Checkpoint").length).toBeGreaterThan(0);
  });

  it("destaca o dia de hoje com blocos e minutos", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", activeCurriculum],
      ["/api/v1/curriculum/day/today", today],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByText(/52 min estimados/)).toBeInTheDocument();
    expect(screen.getByText("Vocabulário")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Começar o dia/ })).toHaveAttribute(
      "href",
      "/cronograma/dia/day-1",
    );
  });

  it("oferece a criação de 90 ou 180 dias quando não há cronograma", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", new ApiError("Nenhum cronograma ativo.", 404, "curriculum_not_found")],
      ["/api/v1/curriculum/day/today", new ApiError("x", 404, "curriculum_not_found")],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByText("Monte seu cronograma de estudo")).toBeInTheDocument();
    expect(screen.getByText("90 dias")).toBeInTheDocument();
    expect(screen.getByText("180 dias")).toBeInTheDocument();
  });

  it("cria o cronograma na duração escolhida", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", new ApiError("x", 404, "curriculum_not_found")],
      ["/api/v1/curriculum/day/today", new ApiError("x", 404, "curriculum_not_found")],
    ]);

    render(<CronogramaPage />);
    await screen.findByText("Monte seu cronograma de estudo");

    fireEvent.click(screen.getByRole("radio", { name: /180 dias/ }));
    fireEvent.click(screen.getByRole("button", { name: "Gerar cronograma" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/curriculum", {
        method: "POST",
        body: { language_code: "en", duration_days: 180 },
      }),
    );
  });

  it("manda fazer o nivelamento quando ele ainda não foi feito", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      [
        "/api/v1/curriculum/active",
        new ApiError("Faça o teste de nivelamento antes.", 409, "placement_required"),
      ],
      ["/api/v1/curriculum/day/today", new ApiError("x", 409, "placement_required")],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByText(/Faça o teste de nivelamento antes/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Fazer teste de nível" })).toHaveAttribute(
      "href",
      "/placement-test",
    );
  });

  it("manda configurar o idioma quando não há perfil linguístico", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      [
        "/api/v1/curriculum/active",
        new ApiError("Idioma não configurado para o usuário.", 404, "language_not_configured"),
      ],
      ["/api/v1/curriculum/day/today", new ApiError("x", 404, "language_not_configured")],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByRole("link", { name: "Configurar idioma" })).toHaveAttribute(
      "href",
      "/onboarding",
    );
  });

  it("mostra erro recuperável quando o carregamento falha", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", new Error("fora do ar")],
      ["/api/v1/curriculum/day/today", new Error("fora do ar")],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});

describe("Atraso e reagendamento", () => {
  const atrasado = {
    ...activeCurriculum,
    progress: { ...progress, overdue_days: 7, needs_reschedule: true },
  };

  it("avisa o atraso e oferece as duas opções", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", atrasado],
      ["/api/v1/curriculum/day/today", today],
    ]);

    render(<CronogramaPage />);

    expect(await screen.findByText("7 dias atrasados")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Comprimir/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Estender/ })).toBeInTheDocument();
  });

  it("explica que nenhuma das opções apaga o que foi concluído", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", atrasado],
      ["/api/v1/curriculum/day/today", today],
    ]);

    render(<CronogramaPage />);
    expect(
      await screen.findByText(/Nenhuma delas apaga o que você já concluiu/),
    ).toBeInTheDocument();
  });

  it("envia a estratégia escolhida", async () => {
    routeApi([
      ["/api/v1/language-profiles", profiles],
      ["/api/v1/curriculum/active", atrasado],
      ["/api/v1/curriculum/day/today", today],
      ["/api/v1/curriculum/cur-1/reschedule", { curriculum, strategy: "extend" }],
    ]);

    render(<CronogramaPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Estender/ }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/curriculum/cur-1/reschedule", {
        method: "POST",
        body: { strategy: "extend" },
      }),
    );
  });
});

describe("Execução do dia", () => {
  const lesson = {
    lesson_id: "les-1",
    mode: "vocabulary",
    provider: "mock",
    language_code: "en",
    level: "A2",
    level_source: "placement_test",
    level_is_estimated: true,
    title: "Vocabulário essencial · A2",
    objective: "Ampliar vocabulário de alta frequência.",
    topic: "Apresentações e rotina — vocabulário essencial",
    items: [
      {
        term: "on my way",
        translation: "a caminho",
        example: "I'm on my way.",
        example_translation: "Estou a caminho.",
        usage_note: "Muito usado em mensagens.",
      },
    ],
  };

  const dayDetail = { curriculum, week, day };

  it("lista os blocos do dia na ordem", async () => {
    routeApi([
      ["/api/v1/curriculum/day/day-1", dayDetail],
      ["/api/v1/curriculum/block/b-1/start", { block: day.blocks[0], lesson }],
    ]);

    render(<CurriculumDayPage />);

    expect(await screen.findByText("Dia 1")).toBeInTheDocument();
    expect(screen.getByText(/Semana 1 · Apresentações e rotina/)).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Caminho do dia" });
    expect(nav).toHaveTextContent("Vocabulário");
    expect(nav).toHaveTextContent("Gramática");
    expect(nav).toHaveTextContent("Revisão");
  });

  it("abre o primeiro bloco pendente automaticamente", async () => {
    routeApi([
      ["/api/v1/curriculum/day/day-1", dayDetail],
      ["/api/v1/curriculum/block/b-1/start", { block: day.blocks[0], lesson }],
    ]);

    render(<CurriculumDayPage />);

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/curriculum/block/b-1/start", {
        method: "POST",
        body: {},
      }),
    );
    expect(await screen.findByText("Vocabulário essencial · A2")).toBeInTheDocument();
    // O tópico do bloco aparece na tela: é o que diferencia esta semana das outras.
    expect(screen.getByText("Apresentações e rotina — vocabulário")).toBeInTheDocument();
  });

  it("conclui o bloco pelo endpoint do cronograma", async () => {
    routeApi([
      ["/api/v1/curriculum/day/day-1", dayDetail],
      ["/api/v1/curriculum/block/b-1/start", { block: day.blocks[0], lesson }],
      [
        "/api/v1/curriculum/block/b-1/complete",
        {
          block: { ...day.blocks[0], status: "completed" },
          day: { id: "day-1", status: "in_progress", completed_at: null },
          day_completed: false,
          progress,
        },
      ],
    ]);

    render(<CurriculumDayPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Concluir e avançar" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/curriculum/block/b-1/complete", {
        method: "POST",
        body: {},
      }),
    );
  });

  it("marca a demonstração quando a lição vem do mock", async () => {
    routeApi([
      ["/api/v1/curriculum/day/day-1", dayDetail],
      ["/api/v1/curriculum/block/b-1/start", { block: day.blocks[0], lesson }],
    ]);

    render(<CurriculumDayPage />);
    expect(await screen.findByText("Gerado em modo mock (IA local)")).toBeInTheDocument();
  });

  it("declara fila vazia no bloco de revisão em vez de inventar itens", async () => {
    routeApi([
      [
        "/api/v1/curriculum/day/day-1",
        {
          ...dayDetail,
          day: {
            ...day,
            blocks: [{ ...day.blocks[2], status: "pending" }],
            blocks_total: 1,
          },
        },
      ],
      [
        "/api/v1/curriculum/block/b-3/start",
        {
          block: day.blocks[2],
          lesson: {
            title: "Revisão espaçada · A2",
            source: "srs_queue",
            queue_empty: true,
            items: [],
            empty_notice: "Nenhum item vencido na fila hoje.",
          },
        },
      ],
    ]);

    render(<CurriculumDayPage />);

    expect(await screen.findByText("Nada vencido na fila")).toBeInTheDocument();
    expect(screen.getByText("Nenhum item vencido na fila hoje.")).toBeInTheDocument();
  });

  it("serve a fila real do SRS quando há item vencido", async () => {
    routeApi([
      [
        "/api/v1/curriculum/day/day-1",
        {
          ...dayDetail,
          day: { ...day, blocks: [{ ...day.blocks[2] }], blocks_total: 1 },
        },
      ],
      [
        "/api/v1/curriculum/block/b-3/start",
        {
          block: day.blocks[2],
          lesson: {
            title: "Revisão espaçada · A2",
            source: "srs_queue",
            queue_empty: false,
            items: [
              {
                review_item_id: "r-1",
                item_type: "vocabulary",
                reference_id: "v-1",
                payload: { term: "water", translation_pt: "água" },
                next_review_at: null,
              },
            ],
          },
        },
      ],
      ["/api/v1/reviews/r-1/answer", { id: "r-1" }],
    ]);

    render(<CurriculumDayPage />);

    expect(await screen.findByText("water")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ver resposta" }));
    expect(await screen.findByText("água")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Bom" }));
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/reviews/r-1/answer", {
        method: "POST",
        body: { rating: "good" },
      }),
    );
  });

  it("anuncia o dia concluído quando não resta bloco", async () => {
    routeApi([
      [
        "/api/v1/curriculum/day/day-1",
        {
          ...dayDetail,
          day: {
            ...day,
            status: "completed",
            blocks_completed: 3,
            blocks: day.blocks.map((item) => ({ ...item, status: "completed" })),
          },
        },
      ],
    ]);

    render(<CurriculumDayPage />);

    expect(await screen.findByText("Dia concluído")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar ao cronograma" })).toHaveAttribute(
      "href",
      "/cronograma",
    );
  });

  it("mostra erro recuperável quando o dia não carrega", async () => {
    dayId = "inexistente";
    routeApi([["/api/v1/curriculum/day/inexistente", new ApiError("Dia não encontrado.", 404)]]);

    render(<CurriculumDayPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Dia não encontrado.");
  });
});
