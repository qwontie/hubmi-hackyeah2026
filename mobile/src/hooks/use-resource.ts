import { useCallback, useEffect, useState } from "react";
import { ApiError, errorMessage } from "@/api/client";
import { isAbort } from "@/lib/options";

export type Resource<T> =
  | { kind: "loading" }
  | { kind: "done"; data: T }
  | { kind: "error"; message: string; missing: boolean };

export const useResource = <T>(
  key: string | undefined,
  load: (key: string, signal: AbortSignal) => Promise<T>
) => {
  const [state, setState] = useState<Resource<T>>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!key || attempt < 0) {
      return;
    }
    const abort = new AbortController();
    setState({ kind: "loading" });
    load(key, abort.signal)
      .then((data) => setState({ data, kind: "done" }))
      .catch((caught: unknown) => {
        if (isAbort(caught)) {
          return;
        }
        setState({
          kind: "error",
          message: errorMessage(caught),
          missing: caught instanceof ApiError && caught.code === "not_found",
        });
      });
    return () => abort.abort();
  }, [key, attempt, load]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  return { retry, state };
};
