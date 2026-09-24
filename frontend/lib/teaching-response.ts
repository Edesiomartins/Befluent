/**
 * Espelha o acknowledgement de `teaching_slice.submit_slice_answer`.
 *
 * Atividades expositivas avançam com «Continuar». `recognition` só é
 * expositiva quando não há `vocabulary_item_id`; com item, é escolha objetiva.
 */

export function activityIsAcknowledgement(activity: {
  type?: string;
  vocabulary_item_id?: string | null;
} | null | undefined): boolean {
  const type = activity?.type ?? "";
  if (
    type === "listen" ||
    type === "matching" ||
    type === "presentation" ||
    type === "conversation_prompt"
  ) {
    return true;
  }
  return type === "recognition" && !activity?.vocabulary_item_id;
}
