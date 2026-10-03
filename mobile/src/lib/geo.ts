import type { PowiatFeature, PowiatGeo } from "@/api/types";

export interface PowiatShape {
  center: { x: number; y: number };
  d: string;
  name: string;
  slug: string;
}

type Ring = number[][];

const ringsOf = (feature: PowiatFeature): Ring[] =>
  feature.geometry.type === "Polygon"
    ? (feature.geometry.coordinates as number[][][])
    : (feature.geometry.coordinates as number[][][][]).flat();

export const projectPowiats = (geo: PowiatGeo, width = 1000) => {
  const all = geo.features.flatMap(ringsOf).flat();
  const lons = all.map((point) => point[0] ?? 0);
  const lats = all.map((point) => point[1] ?? 0);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const midLat = ((minLat + maxLat) / 2) * (Math.PI / 180);
  const xSpan = (maxLon - minLon) * Math.cos(midLat);
  const ySpan = maxLat - minLat;
  const scale = width / xSpan;
  const height = Math.round(ySpan * scale);
  const project = (point: number[]) => ({
    x: ((point[0] ?? 0) - minLon) * Math.cos(midLat) * scale,
    y: (maxLat - (point[1] ?? 0)) * scale,
  });
  const shapes: PowiatShape[] = geo.features.map((feature) => {
    const rings = ringsOf(feature);
    const d = rings
      .map(
        (ring) =>
          `M${ring
            .map((point) => {
              const { x, y } = project(point);
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join("L")}Z`
      )
      .join("");
    const outer = rings[0] ?? [];
    const projected = outer.map(project);
    const center = {
      x: projected.reduce((sum, p) => sum + p.x, 0) / (projected.length || 1),
      y: projected.reduce((sum, p) => sum + p.y, 0) / (projected.length || 1),
    };
    return {
      center,
      d,
      name: feature.properties.name,
      slug: feature.properties.slug,
    };
  });
  return { height, shapes, width };
};
