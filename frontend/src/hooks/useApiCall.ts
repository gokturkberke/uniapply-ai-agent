import { useCallback, useState } from "react";

import { ApiError } from "../api/client";

export interface ApiCall<TData, TArgs extends unknown[]> {
  data: TData | null;
  loading: boolean;
  error: string | null;
  run: (...args: TArgs) => Promise<void>;
  reset: () => void;
}

// Wraps an async API function with loading/error/data state. The wrapped
// function must be stable (module-level or useCallback) since it is a hook
// dependency. Network and HTTP failures surface as a human-readable error
// string; a successful call (including a grounded refusal) sets data.
export function useApiCall<TData, TArgs extends unknown[]>(
  fn: (...args: TArgs) => Promise<TData>,
): ApiCall<TData, TArgs> {
  const [data, setData] = useState<TData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (...args: TArgs): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const result = await fn(...args);
        setData(result);
      } catch (caught) {
        setData(null);
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Unexpected error. Please try again.",
        );
      } finally {
        setLoading(false);
      }
    },
    [fn],
  );

  const reset = useCallback((): void => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, run, reset };
}
