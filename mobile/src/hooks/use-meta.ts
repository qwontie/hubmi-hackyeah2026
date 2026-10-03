import { api } from "@/api/client";
import { useResource } from "./use-resource";

const loadMeta = (_key: string, signal: AbortSignal) => api.meta(signal);

export const useMeta = () => useResource("meta", loadMeta);
