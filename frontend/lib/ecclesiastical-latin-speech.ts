/**
 * Preparação fonética do latim eclesiástico **somente** para o fallback
 * `window.speechSynthesis` (voz italiana `it-IT` como aproximação).
 *
 * - NÃO alterar o texto pedagógico exibido, gabaritos ou currículo.
 * - NÃO usar esta saída como texto visível ao aluno.
 * - A voz italiana é aproximação controlada, não pronúncia litúrgica perfeita.
 *
 * Fontes das regras: SCRIPT_RULES em `learner_context.py`, notas em
 * `lesson_bank_la.py`. O Piper recebe o texto já preparado, com idioma `la`.
 *
 * Limitações conhecidas (documentadas de propósito):
 * - `ti` + vogal → /tsi/ só via léxico explícito (regex ampla seria insegura
 *   após s/t/x; ex.: hostia, mixtio).
 * - Qualidade depende da voz `it-*` instalada no SO/navegador.
 */

/** Ortografia latina → forma ortográfica amigável a um TTS italiano. */
const LEXICON: Record<string, string> = {
  caelum: "celum",
  caeli: "celi",
  caelis: "celis",
  caelo: "celo",
  ecclesia: "ekklezia",
  cecilia: "cecilia",
  regina: "regina",
  angelus: "angelus",
  gratia: "grazia",
  oratio: "orazio",
  iustitia: "iustitsia",
  incarnatio: "incarnatsio",
  regnum: "regno",
  sanctus: "sanctus",
  credo: "credo",
};

function applyCase(source: string, preparedLower: string): string {
  if (!source) return preparedLower;
  if (source === source.toUpperCase()) return preparedLower.toUpperCase();
  if (source[0] === source[0].toUpperCase()) {
    return preparedLower.charAt(0).toUpperCase() + preparedLower.slice(1);
  }
  return preparedLower;
}

/**
 * Regras gerais seguras (após o léxico). Evita regex ampla de `ti`+vogal.
 */
function applySafeRules(lower: string): string {
  let s = lower;
  // digrafos longos primeiro
  s = s.replace(/scae/g, "sce").replace(/scoe/g, "sce");
  s = s.replace(/cae/g, "ce").replace(/coe/g, "ce");
  s = s.replace(/gae/g, "ge").replace(/goe/g, "ge");
  s = s.replace(/ae/g, "e").replace(/oe/g, "e");
  // gn e c/g ante e/i já são lidos corretamente pelo italiano na maioria dos casos
  return s;
}

function transformToken(token: string): string {
  const lower = token.toLowerCase();
  const fromLexicon = LEXICON[lower];
  if (fromLexicon !== undefined) {
    return applyCase(token, fromLexicon);
  }
  return applyCase(token, applySafeRules(lower));
}

/**
 * Converte ortografia latina eclesiástica em texto falável para voz `it-IT`.
 * Preserva pontuação, espaços e capitalização quando possível.
 */
export function prepareEcclesiasticalLatinForSpeech(text: string): string {
  if (!text || !text.trim()) return text;
  // Tokens alfabéticos (inclui letras latinas comuns); resto intacto.
  return text.replace(/[A-Za-zÀ-ÿ]+/g, (word) => transformToken(word));
}
