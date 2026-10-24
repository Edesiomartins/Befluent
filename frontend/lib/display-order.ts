/**
 * Ordem de exibição estável. Não usa Math.random.
 * Se o hash repetir a ordem original, troca as duas primeiras posições.
 */
export function displayOrder(length: number, seed: string): number[] {
  const order = Array.from({ length }, (_, index) => index);
  order.sort((left, right) => {
    const rank = hash(`${seed}:${left}`) - hash(`${seed}:${right}`);
    return rank || left - right;
  });
  const identity = order.every((value, index) => value === index);
  if (identity && order.length > 1) {
    const [first, second] = order;
    order[0] = second;
    order[1] = first;
  }
  return order;
}

function hash(value: string): number {
  let result = 0;
  for (let index = 0; index < value.length; index += 1) {
    result = (result * 33 + value.charCodeAt(index)) >>> 0;
  }
  return result;
}
