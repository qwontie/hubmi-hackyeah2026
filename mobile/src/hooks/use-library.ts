import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { Category, InnovationSummary } from "@/api/types";
import { isAbort } from "@/lib/options";
import { pluralPl } from "@/lib/plural";

const PER_PAGE = 20;

interface ListState {
  error: string | null;
  items: InnovationSummary[];
  loading: boolean;
  page: number;
  total: number;
}

const emptyList: ListState = {
  error: null,
  items: [],
  loading: true,
  page: 0,
  total: 0,
};

export const useLibrary = () => {
  const params = useLocalSearchParams<{ kategoria?: string; q?: string }>();
  const category = params.kategoria ?? "";
  const query = params.q ?? "";
  const [categories, setCategories] = useState<Category[]>([]);
  const [draft, setDraft] = useState(query);
  const [list, setList] = useState<ListState>(emptyList);
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const abort = new AbortController();
    api
      .categories(abort.signal)
      .then(setCategories)
      .catch(() => setCategories([]));
    return () => abort.abort();
  }, []);

  useEffect(() => {
    setDraft(query);
    setPage(1);
  }, [query]);

  useEffect(() => {
    if (attempt < 0) {
      return;
    }
    const abort = new AbortController();
    setList((current) => ({
      ...(page === 1 ? emptyList : current),
      error: null,
      loading: true,
    }));
    api
      .innovations(
        {
          category: category || undefined,
          page,
          per_page: PER_PAGE,
          q: query.length >= 2 ? query : undefined,
        },
        abort.signal
      )
      .then((result) =>
        setList((current) => ({
          error: null,
          items:
            page === 1 ? result.items : [...current.items, ...result.items],
          loading: false,
          page: result.page,
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
  }, [category, query, page, attempt]);

  const selectCategory = (slug: string) => {
    setPage(1);
    router.setParams({ kategoria: slug === category ? "" : slug });
  };

  const search = () => {
    setPage(1);
    router.setParams({ q: draft.trim() });
  };

  const clearSearch = () => {
    setDraft("");
    setPage(1);
    router.setParams({ q: "" });
  };

  const activeCategory = categories.find((item) => item.slug === category);
  const summary = (() => {
    if (list.loading && list.items.length === 0) {
      return "Wczytuję";
    }
    const count = `${list.total} ${pluralPl(
      list.total,
      "rozwiązanie",
      "rozwiązania",
      "rozwiązań"
    )}`;
    return [
      count,
      activeCategory ? activeCategory.name.toLowerCase() : null,
      query ? `dla „${query}”` : null,
    ]
      .filter(Boolean)
      .join(" ");
  })();

  return {
    categories,
    category,
    clearSearch,
    draft,
    hasMore: list.items.length > 0 && list.items.length < list.total,
    list,
    loadMore: () => setPage((value) => value + 1),
    query,
    retry: () => setAttempt((value) => value + 1),
    search,
    selectCategory,
    setDraft,
    summary,
  };
};
