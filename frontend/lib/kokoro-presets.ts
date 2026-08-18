/** Frases padrão do Kokoro Voice Lab, por idioma — texto estático (sem geração
 * por IA em runtime). Cobrem 5 tipos por idioma: frase curta, pergunta,
 * conversação natural, feedback pedagógico e frase mais longa; `length`
 * mapeia esses 5 tipos em Short/Medium/Long para o filtro de tamanho.
 *
 * Inglês usa exatamente os exemplos do briefing da tarefa. Espanhol, francês,
 * japonês e chinês foram escritos à mão com o mesmo espírito (não são
 * traduções automáticas) — não têm a mesma revisão nativa que o inglês, então
 * tratar como ponto de partida, não como referência definitiva de fluência.
 */

export type PresetLength = "short" | "medium" | "long";

export type KokoroPreset = {
  label: string;
  length: PresetLength;
  text: string;
};

const ENGLISH_PRESETS: KokoroPreset[] = [
  { label: "Frase curta", length: "short", text: "Hello! How are you doing today?" },
  { label: "Pergunta", length: "medium", text: "Could you tell me where the nearest train station is?" },
  {
    label: "Conversação natural",
    length: "medium",
    text: "Well... I'm not completely sure. Let me think about it for a second.",
  },
  {
    label: "Feedback pedagógico",
    length: "medium",
    text: "Great job. Your answer was correct, but let's work on making it sound more natural.",
  },
  {
    label: "Frase mais longa",
    length: "long",
    text: "Although I understand your point, I don't entirely agree with your conclusion.",
  },
];

export const KOKORO_VOICE_PRESETS: Record<string, KokoroPreset[]> = {
  "en-US": ENGLISH_PRESETS,
  "en-GB": ENGLISH_PRESETS,
  "es-ES": [
    { label: "Frase curta", length: "short", text: "¡Hola! ¿Cómo estás hoy?" },
    { label: "Pergunta", length: "medium", text: "¿Podrías decirme dónde está la estación más cercana?" },
    {
      label: "Conversação natural",
      length: "medium",
      text: "Bueno... no estoy del todo seguro. Déjame pensarlo un momento.",
    },
    {
      label: "Feedback pedagógico",
      length: "medium",
      text: "Muy bien. Tu respuesta fue correcta, pero vamos a trabajar en que suene más natural.",
    },
    {
      label: "Frase mais longa",
      length: "long",
      text: "Aunque entiendo tu punto de vista, no estoy completamente de acuerdo con tu conclusión.",
    },
  ],
  "fr-FR": [
    { label: "Frase curta", length: "short", text: "Bonjour ! Comment allez-vous aujourd'hui ?" },
    { label: "Pergunta", length: "medium", text: "Pourriez-vous me dire où se trouve la gare la plus proche ?" },
    {
      label: "Conversação natural",
      length: "medium",
      text: "Eh bien... je ne suis pas tout à fait sûr. Laissez-moi y réfléchir un instant.",
    },
    {
      label: "Feedback pedagógico",
      length: "medium",
      text: "Très bien. Votre réponse était correcte, mais travaillons pour qu'elle sonne plus naturelle.",
    },
    {
      label: "Frase mais longa",
      length: "long",
      text: "Bien que je comprenne votre point de vue, je ne suis pas entièrement d'accord avec votre conclusion.",
    },
  ],
  "ja-JP": [
    { label: "Frase curta", length: "short", text: "こんにちは。今日はお元気ですか?" },
    { label: "Pergunta", length: "medium", text: "一番近い駅はどこか教えていただけますか?" },
    {
      label: "Conversação natural",
      length: "medium",
      text: "うーん、ちょっとよく分かりません。少し考えさせてください。",
    },
    {
      label: "Feedback pedagógico",
      length: "medium",
      text: "よくできました。答えは合っていますが、もっと自然に聞こえるように練習しましょう。",
    },
    {
      label: "Frase mais longa",
      length: "long",
      text: "あなたの意見は理解できますが、その結論には完全には同意できません。",
    },
  ],
  "zh-CN": [
    { label: "Frase curta", length: "short", text: "你好!你今天过得怎么样?" },
    { label: "Pergunta", length: "medium", text: "请问最近的车站在哪里?" },
    { label: "Conversação natural", length: "medium", text: "嗯……我不太确定。让我想一想。" },
    {
      label: "Feedback pedagógico",
      length: "medium",
      text: "做得很好。你的回答是对的,不过我们可以让它听起来更自然一些。",
    },
    {
      label: "Frase mais longa",
      length: "long",
      text: "虽然我理解你的观点,但我并不完全同意你的结论。",
    },
  ],
};

export function presetsForLanguage(languageCode: string): KokoroPreset[] {
  return KOKORO_VOICE_PRESETS[languageCode] ?? [];
}
