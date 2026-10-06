import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BilingualText } from "@/components/bilingual-text";
import { NativeLanguageProvider } from "@/components/native-language-context";
import { TeachingActivityBody } from "@/components/teaching-activity";
import { LessonContent } from "@/components/lesson-modes";
import { ErrorState } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { speechText, supportText } from "@/lib/bilingual";
import type { GrammarLesson } from "@/types/lesson";

vi.mock("@/components/study", () => ({
  AudioPlayer: ({ text }: { text: string }) => <p>audio:{text}</p>,
  Recorder: () => null,
}));

vi.mock("@/lib/api", () => ({
  api: vi.fn(() => Promise.resolve({})),
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

const grammar = (extra: Partial<GrammarLesson> = {}): GrammarLesson => ({
  mode: "grammar",
  provider: "mock",
  language_code: "fr",
  level: "A1",
  overall_level: "A1",
  skill: "vocabulary_grammar",
  skill_label: "Gramática",
  level_source: "placement_test",
  level_is_estimated: true,
  title: "Artigos",
  objective: "Reconhecer o artigo.",
  explanation: "En français, l'article change avec le nom.",
  patterns: [],
  examples: [{ sentence: "La logique", translation: "A lógica" }],
  exercises: [],
  ...extra,
});

describe("apoio bilíngue", () => {
  it("mostra o título na língua estudada e a tradução nativa por baixo", () => {
    render(<BilingualText heading target="La logique" native="A lógica" />);
    const title = screen.getByRole("heading", { name: "La logique" });
    const support = screen.getByText("A lógica");
    expect(title.compareDocumentPosition(support) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByText("The logic")).not.toBeInTheDocument();
  });

  it("não usa a tradução como texto de áudio", () => {
    expect(speechText("selon moi")).toBe("selon moi");
    expect(speechText("selon moi")).not.toContain("na minha opinião");
  });

  it("esconde o português legado quando a língua nativa não é o português", () => {
    expect(
      supportText({
        nativeLanguage: "en",
        legacyPortuguese: "na minha opinião",
      }),
    ).toBeNull();
    expect(
      supportText({
        nativeLanguage: "en",
        native: "in my opinion",
        legacyPortuguese: "na minha opinião",
      }),
    ).toBe("in my opinion");
    expect(
      supportText({
        nativeLanguage: "pt-BR",
        legacyPortuguese: "na minha opinião",
      }),
    ).toBe("na minha opinião");
  });

  it("francês com nativo pt-BR mostra o termo e o gloss, e o áudio fica no francês", () => {
    render(
      <NativeLanguageProvider code="pt-BR">
        <TeachingActivityBody
          languageCode="fr"
          response=""
          onResponse={() => {}}
          activity={{
            type: "presentation",
            term: "selon moi",
            translation_pt: "na minha opinião",
            audio_targets: [{ audio_target_type: "vocabulary_item", audio_text: "selon moi" }],
          }}
        />
      </NativeLanguageProvider>,
    );
    expect(screen.getByRole("heading", { name: "selon moi" })).toBeInTheDocument();
    expect(screen.getByText("na minha opinião")).toBeInTheDocument();
    expect(screen.getByText("audio:selon moi")).toBeInTheDocument();
    expect(screen.queryByText("audio:na minha opinião")).not.toBeInTheDocument();
    expect(screen.queryByText(/in my opinion/i)).not.toBeInTheDocument();
  });

  it("alemão com nativo inglês não mostra o gloss em português", () => {
    render(
      <NativeLanguageProvider code="en">
        <TeachingActivityBody
          languageCode="de"
          response=""
          onResponse={() => {}}
          activity={{
            type: "presentation",
            term: "meiner Meinung nach",
            translation: "in my opinion",
            translation_pt: "na minha opinião",
            audio_targets: [{ audio_target_type: "vocabulary_item", audio_text: "meiner Meinung nach" }],
          }}
        />
      </NativeLanguageProvider>,
    );
    expect(screen.getByRole("heading", { name: "meiner Meinung nach" })).toBeInTheDocument();
    expect(screen.getByText("in my opinion")).toBeInTheDocument();
    expect(screen.queryByText("na minha opinião")).not.toBeInTheDocument();
    expect(screen.getByText("audio:meiner Meinung nach")).toBeInTheDocument();
  });

  it("inglês com nativo pt-BR mantém o gloss em português", () => {
    render(
      <NativeLanguageProvider code="pt-BR">
        <TeachingActivityBody
          languageCode="en"
          response=""
          onResponse={() => {}}
          activity={{
            type: "presentation",
            term: "according to me",
            translation_pt: "na minha opinião",
            audio_targets: [{ audio_target_type: "vocabulary_item", audio_text: "according to me" }],
          }}
        />
      </NativeLanguageProvider>,
    );
    expect(screen.getByRole("heading", { name: "according to me" })).toBeInTheDocument();
    expect(screen.getByText("na minha opinião")).toBeInTheDocument();
    expect(screen.getByText("audio:according to me")).toBeInTheDocument();
  });

  it("renderiza La logique e A lógica sem uma terceira língua", () => {
    render(
      <NativeLanguageProvider code="pt-BR">
        <LessonContent
          mode="grammar"
          lesson={grammar({
            logic_title: "La logique",
            logic_title_native: "A lógica",
            explanation_native: "Em francês, o artigo muda com o nome.",
          })}
        />
      </NativeLanguageProvider>,
    );
    expect(screen.getByRole("heading", { name: "La logique" })).toBeInTheDocument();
    expect(screen.getAllByText("A lógica").length).toBeGreaterThan(0);
    expect(screen.getByText("En français, l'article change avec le nom.")).toBeInTheDocument();
    expect(screen.getByText("Em francês, o artigo muda com o nome.")).toBeInTheDocument();
    expect(screen.queryByText("The logic")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "A lógica" })).not.toBeInTheDocument();
  });

  it("traduz o erro de língua nativa ausente e aponta para a escolha", () => {
    render(
      <ErrorState
        error={new ApiError("native_language_required", 422, "native_language_required")}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Escolha sua língua nativa para personalizarmos as explicações de apoio.",
    );
    expect(screen.queryByText("native_language_required")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Escolher língua nativa" })).toHaveAttribute(
      "href",
      "/lingua-nativa",
    );
  });
});
