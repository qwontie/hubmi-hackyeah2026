import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type {
  ChallengeSummary,
  CountedRef,
  Figure,
  MaterialSummary,
  Page,
} from "@/api/types";
import { isAbort } from "@/lib/options";
import { useResource } from "./use-resource";

export const AI_SUMMARY_NOTE =
  "Streszczenie przygotowane automatycznie na podstawie dokumentu.";
export const AI_CHALLENGE_NOTE =
  "Opracowanie automatyczne na podstawie dokumentu ROPS.";
export const NATIONAL_NOTE = "Dane dla całej Polski.";

export const figureSource = (figure: Figure) => ({
  label: `Źródło: ${figure.document_title}, s. ${figure.page}`,
  url: `${figure.document_url}#page=${figure.page}`,
});

export const fileLabel = (material: MaterialSummary) => {
  const parts = ["PDF"];
  if (material.pages) {
    parts.push(`${material.pages} s.`);
  }
  if (material.file_size) {
    const megabytes = material.file_size / (1024 * 1024);
    parts.push(
      megabytes >= 1
        ? `${megabytes.toFixed(1).replace(".", ",")} MB`
        : `${Math.max(1, Math.round(material.file_size / 1024))} kB`
    );
  }
  return parts.join(", ");
};

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

const usePagedList = <T>(
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

const useFilterParams = () => {
  const params = useLocalSearchParams<{
    q?: string;
    rodzaj?: string;
    temat?: string;
    obszar?: string;
  }>();
  const [draft, setDraft] = useState(params.q ?? "");
  useEffect(() => {
    setDraft(params.q ?? "");
  }, [params.q]);
  return {
    clearSearch: () => {
      setDraft("");
      router.setParams({ q: "" });
    },
    draft,
    params,
    search: () => router.setParams({ q: draft.trim() }),
    setDraft,
  };
};

export const useChallenges = () => {
  const filters = useFilterParams();
  const area = filters.params.obszar ?? "";
  const q = filters.params.q ?? "";
  const [areas, setAreas] = useState<CountedRef[]>([]);

  useEffect(() => {
    const abort = new AbortController();
    api
      .challengeAreas(abort.signal)
      .then(setAreas)
      .catch(() => setAreas([]));
    return () => abort.abort();
  }, []);

  const load = useCallback(
    (page: number, signal: AbortSignal) =>
      api.challenges(
        {
          area: area || undefined,
          page,
          per_page: 50,
          q: q.length >= 2 ? q : undefined,
        },
        signal
      ),
    [area, q]
  );
  const paged = usePagedList<ChallengeSummary>(`${area}|${q}`, load);

  return {
    ...paged,
    ...filters,
    area,
    areas,
    query: q,
    selectArea: (slug: string) =>
      router.setParams({ obszar: slug === area ? "" : slug }),
  };
};

export const useMaterials = () => {
  const filters = useFilterParams();
  const topic = filters.params.temat ?? "";
  const kind = filters.params.rodzaj ?? "";
  const q = filters.params.q ?? "";
  const [topics, setTopics] = useState<CountedRef[]>([]);
  const [kinds, setKinds] = useState<CountedRef[]>([]);

  useEffect(() => {
    const abort = new AbortController();
    api
      .materialFilters(abort.signal)
      .then((result) => {
        setTopics(result.topics.filter((item) => item.count > 0));
        setKinds(result.kinds.filter((item) => item.count > 0));
      })
      .catch(() => {
        setTopics([]);
        setKinds([]);
      });
    return () => abort.abort();
  }, []);

  const load = useCallback(
    (page: number, signal: AbortSignal) =>
      api.materials(
        {
          kind: kind || undefined,
          page,
          per_page: 20,
          q: q.length >= 2 ? q : undefined,
          topic: topic || undefined,
        },
        signal
      ),
    [kind, topic, q]
  );
  const paged = usePagedList<MaterialSummary>(`${kind}|${topic}|${q}`, load);

  return {
    ...paged,
    ...filters,
    kind,
    kinds,
    query: q,
    selectKind: (slug: string) =>
      router.setParams({ rodzaj: slug === kind ? "" : slug }),
    selectTopic: (slug: string) =>
      router.setParams({ temat: slug === topic ? "" : slug }),
    topic,
    topics,
  };
};

export const useMaterial = (id: string | undefined) =>
  useResource(id, api.material);

export const useChallenge = (key: string | undefined) =>
  useResource(key, api.challenge);
