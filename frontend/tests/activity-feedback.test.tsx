import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActivityFeedback } from "@/components/activities/activity-feedback";

const wrong = {
  is_correct: false,
  selected: "Rome",
  correct_option: "Ada",
  why_selected: "Rome não é a pessoa.",
  why_correct: "Ada chegou.",
  remember: "O sujeito vem antes do verbo.",
};

describe("feedback da atividade", () => {
  it("explica o erro e mantém a mesma atividade na nova tentativa", () => {
    render(<ActivityFeedback feedback={wrong} />);
    expect(screen.getByText("Resposta incorreta")).toBeInTheDocument();
    expect(screen.getByText(/Rome não é a pessoa/)).toBeInTheDocument();
    expect(screen.getByText(/Ada chegou/)).toBeInTheDocument();
    expect(screen.getByText(/mantém esta atividade/)).toBeInTheDocument();
  });

  it("não promete a mesma atividade quando a sessão já avançou", () => {
    render(<ActivityFeedback feedback={wrong} showRetryNote={false} />);
    expect(screen.getByText("Resposta incorreta")).toBeInTheDocument();
    expect(screen.queryByText(/mantém esta atividade/)).not.toBeInTheDocument();
    expect(screen.queryByText(/outra interação/)).not.toBeInTheDocument();
  });

  it("só anuncia outra interação quando o backend mandou essa troca", () => {
    render(<ActivityFeedback feedback={wrong} sameObjectiveRetry={false} />);
    expect(screen.getByText(/Esta tentativa usa outra interação/)).toBeInTheDocument();
  });
});
