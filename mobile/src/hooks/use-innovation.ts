import { useEffect, useRef } from "react";
import type { Text } from "react-native";
import { api } from "@/api/client";
import type { InnovationDetail } from "@/api/types";
import { focusElement } from "@/lib/a11y";
import { plainText } from "@/lib/blocks";
import { useResource } from "./use-resource";

export const innovationSections = (innovation: InnovationDetail) =>
  [
    { body: innovation.what_it_is, title: "Na czym polega rozwiązanie?" },
    { body: innovation.problems, title: "Jakich problemów dotyczy?" },
    { body: innovation.target_group, title: "Dla kogo jest to rozwiązanie?" },
    { body: innovation.who_can_use, title: "Kto może z niego skorzystać?" },
    { body: innovation.effectiveness ?? "", title: "Czy to działa?" },
  ].filter((section) => section.body.trim().length > 0);

export const innovationSpeech = (innovation: InnovationDetail) =>
  [
    innovation.title,
    innovation.lead,
    ...innovationSections(innovation).map(
      (section) => `${section.title} ${plainText(section.body)}`
    ),
  ].join(". ");

export const innovationMeta = (innovation: InnovationDetail) =>
  [
    innovation.category.name,
    innovation.authors.length > 0
      ? `Autorzy: ${innovation.authors.join(", ")}`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

export const useInnovation = (slug: string | undefined) => {
  const { state, retry } = useResource(slug, api.innovation);
  const titleRef = useRef<Text>(null);

  useEffect(() => {
    if (state.kind === "done") {
      focusElement(titleRef.current);
    }
  }, [state.kind]);

  return { retry, state, titleRef };
};
