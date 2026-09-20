/**
 * Preparação fonética do latim clássico **somente** para o fallback
 * `window.speechSynthesis` (modo de teste).
 *
 * - NÃO alterar o texto pedagógico exibido, gabaritos ou currículo.
 * - NÃO usar esta saída como texto visível ao aluno.
 * - NÃO passar `la-classical` para voz Kokoro / `_voice_for_language`.
 * - A qualidade depende da voz do navegador; validação auditiva humana é
 *   obrigatória antes de declarar o áudio “validado”.
 *
 * Convenção: c/g duros (via “k”/“g”), v≈/w/, ae/oe como ditongos aproximados.
 * Isto é aproximação ortográfica para TTS, não IPA perfeita.
 */

const LEXICON: Record<string, string> = {
  caelum: "kai-lum",
  caesar: "kai-sar",
  cicero: "ki-ke-ro",
  ecclesia: "ek-kle-si-a",
  via: "wi-a",
  vinum: "wi-num",
  gratia: "gra-ti-a",
  ratio: "ra-ti-o",
  regina: "re-gi-na",
  angelus: "an-ge-lus",
  sanctus: "sank-tus",
  credo: "kre-do",
  quattuor: "kwat-tu-or",
  philosophia: "phi-lo-so-phi-a",
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
 * Regras gerais seguras (após o léxico) para aproximar clássico no TTS.
 * Evita a monotongação eclesiástica ae→e e o soft-c italiano.
 */
function applySafeRules(lower: string): string {
  let s = lower;
  s = s.replace(/ae/g, "ai").replace(/oe/g, "oi");
  // c duro ante e/i/y (aproximação: k)
  s = s.replace(/c([eiy])/g, "k$1");
  // v consonantal ≈ w (entre vogais / início de sílaba — heurística simples)
  s = s.replace(/\bv/g, "w").replace(/([aeiou])v([aeiou])/g, "$1w$2");
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
 * Converte ortografia latina clássica em texto falável para speechSynthesis
 * em modo de teste. Preserva pontuação e capitalização quando possível.
 */
export function prepareClassicalLatinForSpeech(text: string): string {
  if (!text || !text.trim()) return text;
  return text.replace(/[A-Za-zÀ-ÿ]+/g, (word) => transformToken(word));
}
