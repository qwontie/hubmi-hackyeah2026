import { useCallback } from "react";
import { api } from "@/api/client";
import type { InnovationSummary } from "@/api/types";
import { usePagedList } from "./use-paged-list";

const PAGE_SIZE = 20;

export const useTestOpportunities = () => {
  const load = useCallback(
    (page: number, signal: AbortSignal) =>
      api.innovations({ page, per_page: PAGE_SIZE }, signal),
    []
  );
  return usePagedList<InnovationSummary>("test-opportunities", load);
};
