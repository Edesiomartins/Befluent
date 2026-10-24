import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { TeachingActivityBody } from "@/components/teaching-activity";
import { ActivityFeedback } from "@/components/activities/activity-feedback";
import { ActivityShell } from "@/components/activities/activity-shell";
import { SessionSummary } from "@/components/activities/session-summary";
import type { TeachingActivity } from "@/types/teaching";

const axeOptions = {
  rules: {
    "color-contrast": { enabled: false },
  },
};

function renderBody(activity: TeachingActivity) {
  const onResponse = vi.fn();
  const view = render(
    <TeachingActivityBody activity={activity} response="" onResponse={onResponse} />,
  );
  return { ...view, onResponse };
}

const families: Array<{ family: string; activity: TeachingActivity }> = [
  { family: "presentation", activity: { type: "presentation", term: "bonjour", prompt_native: "Ouça." } },
  { family: "choice", activity: { type: "multiple_choice", prompt: "Qui ?", options: ["Ada", "Rome"] } },
  {
    family: "audio_choice",
    activity: {
      type: "listening_recognition",
      audio_text: "bonjour",
      options: ["oi", "tchau"],
      show_text: false,
    },
  },
  { family: "inline_gap", activity: { type: "fill_gap", prompt: "Je ___ demain." } },
  { family: "tap_order", activity: { type: "word_order", tokens: ["Je", "suis"] } },
  {
    family: "pair_match",
    activity: { type: "matching", pairs: [{ term: "clé", hint_pt: "chave" }] },
  },
  { family: "recall", activity: { type: "lexical_production", prompt: "obrigado" } },
  { family: "guided_input", activity: { type: "guided_production", prompt: "Dites bonjour." } },
  { family: "open_input", activity: { type: "free_production", prompt: "Parlez de votre journée." } },
  { family: "speech_repeat", activity: { type: "repeat", prompt: "Bonjour.", audio_text: "Bonjour." } },
  { family: "dialogue", activity: { type: "conversation_prompt", scenario_target: "À la gare." } },
  { family: "transfer", activity: { type: "transfer_question", prompt_target: "Demandez le quai." } },
  {
    family: "dictation",
    activity: { type: "dictation", audio_text: "Je suis d'accord.", show_text: false },
  },
];

describe("acessibilidade das atividades", () => {
  it.each(families)("$family passa na checagem automática e tem nome acessível", async ({ activity }) => {
    const { container } = renderBody(activity);
    const results = await axe(container, axeOptions);
    expect(results.violations).toEqual([]);
  });

  it("setas movem a escolha e o foco", () => {
    const { onResponse } = renderBody({
      type: "multiple_choice",
      prompt: "Qui ?",
      options: ["Ada", "Rome"],
    });
    const first = screen.getByRole("radio", { name: "Ada" });
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowDown" });
    expect(onResponse).toHaveBeenCalledWith("Rome");
    expect(screen.getByRole("radio", { name: "Rome" })).toHaveFocus();
  });

  it("setas movem o foco entre as palavras disponíveis", () => {
    renderBody({ type: "word_order", tokens: ["Je", "suis"] });
    const words = screen.getByRole("group", { name: "Palavras disponíveis" });
    const [first] = Array.from(words.querySelectorAll("button"));
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(document.activeElement).not.toBe(first);
    expect(words.contains(document.activeElement)).toBe(true);
  });

  it("setas movem o foco entre os itens do par", () => {
    renderBody({
      type: "matching",
      pairs: [
        { term: "clé", hint_pt: "chave" },
        { term: "porte", hint_pt: "porta" },
      ],
    });
    const group = screen.getByRole("group", { name: "Itens" });
    const [first, second] = Array.from(group.querySelectorAll("button"));
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(document.activeElement).toBe(second);
  });

  it("o feedback recebe o foco", () => {
    render(
      <ActivityFeedback
        feedback={{
          is_correct: false,
          selected: "Rome",
          correct_option: "Ada",
          why_selected: "Não é a pessoa.",
          why_correct: "Ada chegou.",
        }}
      />,
    );
    expect(document.activeElement).toHaveTextContent("Resposta incorreta");
  });

  it("shell, jornada mínima e resumo passam na checagem automática", async () => {
    const shell = render(
      <ActivityShell phase="practicing" step={1} total={4} objective="Pedir informação.">
        <p>Atividade</p>
      </ActivityShell>,
    );
    const shellResults = await axe(shell.container, axeOptions);
    expect(shellResults.violations).toEqual([]);
    shell.unmount();

    const summary = render(
      <SessionSummary total={4} completed={4} masteryState="needs_review" />,
    );
    expect((await axe(summary.container, axeOptions)).violations).toEqual([]);
  });
});
