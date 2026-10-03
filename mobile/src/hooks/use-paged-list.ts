import { useEffect, useState } from "react";
import { errorMessage } from "@/api/client";
import type { Page } from "@/api/types";
import { isAbort } from "@/lib/options";

interface ListState<T> {
  error: string | null;
  items: T[];
  loading: boolean;
  total: number;
}

const emptyList = <T>(): ListState<T> => ({
  error: null,
  items: [],
  loading: true,
  total: 0,
});

export const usePagedList = <T>(
  key: string,
  load: (page: number, signal: AbortSignal) => Promise<Page<T>>
) => {
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const [list, setList] = useState<ListState<T>>(emptyList);

  const [pageKey, setPageKey] = useState(key);
  if (pageKey !== key) {
    setPageKey(key);
    setPage(1);
  }

  useEffect(() => {
    if (attempt < 0) {
      return;
    }
    const abort = new AbortController();
    setList((current) => ({
      ...(page === 1 ? emptyList<T>() : current),
      error: null,
      loading: true,
    }));
    load(page, abort.signal)
      .then((result) =>
        setList((current) => ({
          error: null,
          items:
            page === 1 ? result.items : [...current.items, ...result.items],
          loading: false,
          total: result.total,
        }))
      )
      .catch((caught: unknown) => {
        if (isAbort(caught)) {
          return;
        }
        setList((current) => ({
          ...current,
          error: errorMessage(caught),
          loading: false,
        }));
      });
    return () => abort.abort();
  }, [load, page, attempt]);

  return {
    hasMore: list.items.length > 0 && list.items.length < list.total,
    list,
    loadMore: () => setPage((value) => value + 1),
    retry: () => setAttempt((value) => value + 1),
  };
};
