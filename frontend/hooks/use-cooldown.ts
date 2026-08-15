import { useEffect, useState } from "react";

/**
 * Contagem regressiva em segundos, reiniciada sempre que `trigger` muda.
 * Usado para refletir o cooldown de 30s do circuit breaker de IA no backend
 * (`provider_resilience.py`) — sem isso, o botão "tentar novamente" falha
 * instantaneamente enquanto o circuito está aberto, parecendo quebrado.
 * Só conta quando `active` é true; caso contrário fica parado em `seconds`.
 */
export function useCooldown(seconds: number, trigger: unknown, active: boolean): number {
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    if (!active) {
      setRemaining(seconds);
      return;
    }
    setRemaining(seconds);
    const interval = setInterval(() => {
      setRemaining((current) => Math.max(0, current - 1));
    }, 1000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger, active]);

  return remaining;
}
