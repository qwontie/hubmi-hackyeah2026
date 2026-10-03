import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";
import type { Category, Problem } from "@/api/types";
import { DEMO_WORDS } from "@/hooks/use-demo";
import { pluralPl } from "@/lib/plural";
import { useFilterParams } from "./use-knowledge";
import { usePagedList } from "./use-paged-list";
import { useResource } from "./use-resource";

export const proposeHref = (problemId: string) => ({
  params: { problem: problemId },
  pathname: "/pomysl/nowy" as const,
});

export const PROBLEM_SUMMARY_NOTE =
  "Nazwę i opis problemu przygotowano automatycznie ze zgłoszeń mieszkańców.";

export const problemStats = (problem: Problem, demo = false) =>
  [
    `${problem.needs_total} ${pluralPl(problem.needs_total, "zgłoszenie", "zgłoszenia", "zgłoszeń")}`,
    problem.needs_answered > 0
      ? `${problem.needs_answered} z odpowiedzią ROPS`
      : null,
    problem.ideas_count > 0
      ? `${problem.ideas_count} ${pluralPl(problem.ideas_count, "pomysł", "pomysły", "pomysłów")}`
      : null,
    demo ? DEMO_WORDS : null,
  ]
    .filter(Boolean)
    .join(" · ");

export const useProblems = () => {
  const filters = useFilterParams();
  const params = useLocalSearchParams<{
    kategoria?: string;
    powiat?: string;
  }>();
  const category = params.kategoria ?? "";
  const powiat = params.powiat ?? "";
  const q = filters.params.q ?? "";
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    const abort = new AbortController();
    api
      .categories(abort.signal)
      .then(setCategories)
      .catch(() => setCategories([]));
    return () => abort.abort();
  }, []);

  const load = useCallback(
    (page: number, signal: AbortSignal) =>
      api.problems(
        {
          category: category || undefined,
          page,
          per_page: 20,
          powiat: powiat || undefined,
          q: q.length >= 2 ? q : undefined,
        },
        signal
      ),
    [category, powiat, q]
  );
  const paged = usePagedList<Problem>(`${category}|${powiat}|${q}`, load);

  return {
    ...paged,
    ...filters,
    categories,
    category,
    powiat,
    propose: (problemId: string) => router.push(proposeHref(problemId)),
    query: q,
    selectCategory: (slug: string) =>
      router.setParams({ kategoria: slug === category ? "" : slug }),
    selectPowiat: (slug: string) =>
      router.setParams({ powiat: slug === powiat ? "" : slug }),
  };
};

export const useProblem = (id: string | undefined) => {
  const resource = useResource(id, api.problem);
  return {
    ...resource,
    propose: () => {
      if (id) {
        router.push(proposeHref(id));
      }
    },
  };
};
