/** Forma contextual já declarada no item. A tela não conjuga nem compara a frase. */

export type LexicalFormSource = {
  term: string;
  example_form?: string | null;
  form_note?: string | null;
};

export type VisibleContextualForm = {
  exampleForm: string;
  formNote: string;
};

function clean(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function sameForm(left: string, right: string): boolean {
  return left.toLocaleLowerCase() === right.toLocaleLowerCase();
}

/** Devolve a forma para exibir, ou null quando o dado não existe ou é redundante. */
export function visibleContextualForm(item: LexicalFormSource): VisibleContextualForm | null {
  const term = clean(item.term);
  const form = clean(item.example_form);
  const note = clean(item.form_note);
  if (!form || sameForm(form, term)) return null;
  return { exampleForm: form, formNote: note };
}
