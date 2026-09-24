import { describe, expect, it } from "vitest";
import { coachFor } from "@/lib/coach";
import { conversationTopic, deriveDailyMission, missionCta } from "@/lib/journey";
import type { CurriculumDay } from "@/types/curriculum";

function day(partial: Partial<CurriculumDay> = {}): CurriculumDay {
  return {
    id: "day-fr",
    day_number: 12,
    scheduled_date: "2026-09-23",
    status: "pending",
    completed_at: null,
    total_minutes: 18,
    blocks_total: 2,
    blocks_completed: 0,
    blocks: [
      {
        id: "b1",
        skill: "vocabulary",
        skill_label: "Vocabulário",
        mode: "vocabulary",
        position: 1,
        estimated_minutes: 8,
        cefr_level: "B1",
        topic: "Fazer check-in em um hotel",
        lesson_ref: null,
        status: "pending",
        score: null,
        phase: "activate",
        phase_label: "Ativar",
      },
      {
        id: "b2",
        skill: "conversation",
        skill_label: "Conversação",
        mode: "conversation",
        position: 2,
        estimated_minutes: 10,
        cefr_level: "B1",
        topic: "Recepção",
        lesson_ref: null,
        status: "pending",
        score: null,
        phase: "output",
        phase_label: "Produzir",
      },
    ],
    learning_objective: {
      id: "obj",
      code: "FR-B1",
      title: "Hotel",
      can_do: "can check in",
      learner_goal: "Confirmar a reserva na recepção.",
      level: "B1",
      state: "practicing",
      status_label: "Em prática",
      reasons: [],
    },
    ...partial,
  };
}

describe("Journey", () => {
  it("deriva a missão do objetivo e dos blocos reais", () => {
    const mission = deriveDailyMission({
      day: day(),
      weekTheme: "Viagens",
      languageName: "Francês",
      level: "B1",
    });
    expect(mission.title).toBe("Confirmar a reserva na recepção.");
    expect(mission.language_name).toBe("Francês");
    expect(mission.level).toBe("B1");
    expect(mission.progress_current).toBe(0);
    expect(mission.progress_total).toBe(2);
    expect(mission.phases.map((phase) => phase.label)).toEqual(["Preparar", "Usar"]);
    expect(missionCta(mission.status)).toBe("Começar missão");
  });

  it("continua a missão quando há bloco concluído", () => {
    const source = day();
    source.blocks[0] = { ...source.blocks[0], status: "completed" };
    source.blocks_completed = 1;
    source.status = "in_progress";
    const mission = deriveDailyMission({
      day: source,
      languageName: "Francês",
    });
    expect(mission.status).toBe("in_progress");
    expect(missionCta(mission.status)).toBe("Continuar missão");
    expect(mission.phases[0]?.state).toBe("done");
    expect(mission.phases[1]?.state).toBe("current");
  });

  it("marca missão concluída sem tratar isso como domínio", () => {
    const source = day({ status: "completed", blocks_completed: 2 });
    source.blocks = source.blocks.map((block) => ({ ...block, status: "completed" }));
    const mission = deriveDailyMission({ day: source, languageName: "Francês" });
    expect(mission.status).toBe("completed");
    expect(missionCta(mission.status)).toBe("Missão concluída");
  });

  it("cai no tema da semana quando não há objetivo nem tópico", () => {
    const source = day({ learning_objective: null });
    source.blocks = source.blocks.map((block) => ({ ...block, topic: "" }));
    const mission = deriveDailyMission({
      day: source,
      weekTheme: "Apresentações e rotina",
      languageName: "Inglês",
    });
    expect(mission.title).toBe("Apresentações e rotina");
  });

  it("não mistura missão de outro idioma: o nome vem do payload atual", () => {
    const french = deriveDailyMission({ day: day(), languageName: "Francês" });
    const japanese = deriveDailyMission({
      day: { ...day(), id: "day-ja" },
      languageName: "Japonês",
    });
    expect(french.language_name).toBe("Francês");
    expect(japanese.language_name).toBe("Japonês");
    expect(japanese.day_id).toBe("day-ja");
  });

  it("conversa da missão usa o cenário; prática livre permanece independente", () => {
    expect(
      conversationTopic({
        lessonSituation: "Conversa livre",
        missionScenario: "Fazer check-in em um hotel",
      }),
    ).toBe("Fazer check-in em um hotel");
    expect(
      conversationTopic({
        lessonSituation: "Na recepção do hotel",
        missionScenario: "Outro",
      }),
    ).toBe("Na recepção do hotel");
    expect(
      conversationTopic({ lessonSituation: "", freePractice: true }),
    ).toBe("Conversa livre");
  });

  it("coach é por idioma e não quebra códigos especiais", () => {
    expect(coachFor("fr").display_name).toBe("Camille");
    expect(coachFor("ja").language_code).toBe("ja");
    expect(coachFor("zh-CN").display_name).toBe("Mei");
    expect(coachFor("la-classical").short_role).toContain("clássico");
    expect(coachFor("xx").display_name).toBe("Coach");
  });
});
