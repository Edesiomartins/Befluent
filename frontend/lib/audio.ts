/** Decodifica áudio `base64` (resposta do TTS Lab) para `Blob`, para tocar em
 * `<audio>` via `URL.createObjectURL`. Usado pelo TTS Lab genérico e pelo
 * Kokoro Voice Lab — nenhum outro fluxo do produto usa esta função. */
export function base64ToBlob(base64: string, contentType: string): Blob {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: contentType });
}
