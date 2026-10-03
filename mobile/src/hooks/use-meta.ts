import { useCallback } from "react";
import { api } from "@/api/client";
import { useResource } from "./use-resource";

const loadMeta = (_key: string, signal: AbortSignal) => api.meta(signal);

export const useMeta = () => {
  const load = useCallback(loadMeta, []);
  return useResource("meta", load);
};
