export type StartGate = {
  id: string | null;
  pending: Promise<string> | null;
  /** Definido pela resposta de abertura. Ausente até o servidor responder. */
  openingRejected?: boolean;
};

export function claimConversation(
  gate: StartGate,
  start: () => Promise<string>,
): Promise<string> {
  if (gate.id) return Promise.resolve(gate.id);
  if (gate.pending) return gate.pending;
  const pending = start()
    .then((id) => {
      gate.id = id;
      return id;
    })
    .finally(() => {
      if (gate.pending === pending) gate.pending = null;
    });
  gate.pending = pending;
  return pending;
}

export function turnStillCurrent(sentFor: string, activeId: string | null): boolean {
  return activeId === sentFor;
}
