import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { Powiat } from "@/api/types";
import type { SelectOption } from "@/lib/options";

export const usePowiats = () => {
  const [powiats, setPowiats] = useState<Powiat[]>([]);
  useEffect(() => {
    const abort = new AbortController();
    api
      .powiats(abort.signal)
      .then(setPowiats)
      .catch(() => setPowiats([]));
    return () => abort.abort();
  }, []);
  const options: SelectOption[] = powiats.map((item) => ({
    label: item.name,
    value: item.slug,
  }));
  return { options, powiats };
};
