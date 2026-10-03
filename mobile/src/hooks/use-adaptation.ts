import { router } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { AdaptationPlan, InstitutionType } from "@/api/types";
import { isAbort, type SelectOption } from "@/lib/options";
import { fieldMessage } from "@/lib/validation";
import { useResource } from "./use-resource";

interface FormErrors {
  context: string | null;
  institution: string | null;
  place: string | null;
}

const noErrors: FormErrors = { context: null, institution: null, place: null };

const validate = (
  institution: string,
  place: string,
  context: string
): FormErrors => ({
  context:
    context.length < 20
      ? "Opisz sytuację instytucji (co najmniej 20 znaków): kim są odbiorcy, jaki jest zespół i budżet."
      : null,
  institution: institution ? null : "Wybierz rodzaj instytucji.",
  place:
    place.length < 2 ? "Wpisz gminę, miejscowość albo nazwę instytucji." : null,
});

export const PLAN_LISTS: { key: keyof AdaptationPlan; title: string }[] = [
  { key: "staff", title: "Kogo potrzeba" },
  { key: "partners", title: "Z kim współpracować" },
  { key: "cost_drivers", title: "Od czego zależy koszt" },
  { key: "measures", title: "Co mierzyć" },
  { key: "to_check", title: "Do sprawdzenia u siebie" },
];

export const planSpeech = (plan: AdaptationPlan) =>
  [
    plan.service_name,
    plan.summary,
    `Dla kogo: ${plan.target_group}`,
    "Jak zacząć:",
    ...plan.steps.map(
      (step, index) => `Krok ${index + 1}: ${step.title}. ${step.description}`
    ),
  ].join(" ");

export const useAdaptForm = (slug: string | undefined) => {
  const [title, setTitle] = useState<string | null>(null);
  const [types, setTypes] = useState<InstitutionType[]>([]);
  const [institution, setInstitution] = useState("");
  const [place, setPlace] = useState("");
  const [powiat, setPowiat] = useState("");
  const [context, setContext] = useState("");
  const [errors, setErrors] = useState<FormErrors>(noErrors);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!slug) {
      return;
    }
    const abort = new AbortController();
    api
      .innovation(slug, abort.signal)
      .then((innovation) => setTitle(innovation.title))
      .catch(() => setTitle(null));
    api
      .institutionTypes(abort.signal)
      .then(setTypes)
      .catch(() => setTypes([]));
    return () => {
      abort.abort();
      controller.current?.abort();
    };
  }, [slug]);

  const submit = async () => {
    if (!slug) {
      return;
    }
    const problems = validate(institution, place.trim(), context.trim());
    setErrors(problems);
    if (problems.institution || problems.place || problems.context) {
      return;
    }
    setBusy(true);
    setError(null);
    controller.current = new AbortController();
    try {
      const adaptation = await api.adapt(
        slug,
        {
          context: context.trim(),
          institution_type: institution,
          place: place.trim(),
          ...(powiat ? { powiat } : {}),
        },
        controller.current.signal
      );
      router.replace({
        params: { id: adaptation.id },
        pathname: "/adaptacja/[id]",
      });
    } catch (caught) {
      if (isAbort(caught)) {
        return;
      }
      setErrors({
        context: fieldMessage(caught, "context"),
        institution: fieldMessage(caught, "institution_type"),
        place: fieldMessage(caught, "place"),
      });
      setError(errorMessage(caught));
      setBusy(false);
    }
  };

  const institutionOptions: SelectOption[] = types.map((item) => ({
    label: item.name,
    value: item.slug,
  }));

  return {
    busy,
    context,
    error,
    errors,
    institution,
    institutionOptions,
    place,
    powiat,
    setContext,
    setInstitution,
    setPlace,
    setPowiat,
    submit,
    title,
  };
};

export const useAdaptation = (id: string | undefined) =>
  useResource(id, api.adaptation);
