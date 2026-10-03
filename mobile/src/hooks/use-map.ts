import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { MapData, MapPowiat, PowiatGeo } from "@/api/types";
import { projectPowiats } from "@/lib/geo";
import { isAbort } from "@/lib/options";

export const MAP_ATTRIBUTION = "Granice: GUGiK (PRG)";

type Load =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; data: MapData; geo: PowiatGeo };

export const hasNeedCounts = (data: MapData) =>
  data.powiats.some((item) => item.needs_open !== undefined);

export const useMap = () => {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [indicatorKey, setIndicatorKey] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (attempt < 0) {
      return;
    }
    const abort = new AbortController();
    setLoad({ kind: "loading" });
    api
      .map(abort.signal)
      .then(async (mapData) => {
        const geo = await api.mapGeo(mapData.geojson_url, abort.signal);
        setLoad({ data: mapData, geo, kind: "done" });
        setIndicatorKey(
          (current) => current ?? mapData.indicators[0]?.key ?? null
        );
      })
      .catch((caught: unknown) => {
        if (!isAbort(caught)) {
          setLoad({ kind: "error", message: errorMessage(caught) });
        }
      });
    return () => abort.abort();
  }, [attempt]);

  const projection = useMemo(
    () => (load.kind === "done" ? projectPowiats(load.geo) : null),
    [load]
  );

  const data = load.kind === "done" ? load.data : null;
  const indicator =
    data?.indicators.find((item) => item.key === indicatorKey) ?? null;

  const shade = (slug: string) => {
    const powiat = data?.powiats.find((item) => item.slug === slug);
    if (!(powiat && indicator)) {
      return null;
    }
    const figure = powiat.figures.find((item) => item.key === indicator.key);
    if (!figure || indicator.max === indicator.min) {
      return null;
    }
    return (figure.value - indicator.min) / (indicator.max - indicator.min);
  };

  const selectedPowiat: MapPowiat | null =
    data?.powiats.find((item) => item.slug === selected) ?? null;

  return {
    data,
    indicator,
    load,
    projection,
    report: (slug: string) =>
      router.push({ params: { powiat: slug }, pathname: "/" }),
    retry: () => setAttempt((value) => value + 1),
    select: setSelected,
    selected: selectedPowiat,
    setIndicator: setIndicatorKey,
    shade,
  };
};
