"use client";

import { useCallback, useState } from "react";

export function useAsync<T, A extends unknown[]>(operation: (...args: A) => Promise<T>) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(false);
  const run = useCallback(async (...args: A) => {
    setLoading(true); setError(undefined);
    try {
      const result = await operation(...args);
      setData(result);
      return result;
    } catch (caught) {
      const nextError = caught instanceof Error ? caught : new Error("Falha inesperada");
      setError(nextError);
      throw nextError;
    } finally {
      setLoading(false);
    }
  }, [operation]);
  return { data, error, loading, run };
}
