import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ApiError, api, errorMessage } from "@/api/client";
import type {
  AssistAnswer,
  AssistOut,
  Canvas,
  IdeaCreated,
  IdeaDraft,
  IdeaOptions,
} from "@/api/types";
import type { SelectOption } from "@/lib/options";
import { EMAIL_INVALID, isEmail } from "@/lib/validation";
import { saveIdea } from "@/storage/ideas";

type Field =
  | "title"
  | "essence"
  | "for_whom"
  | "contact_email"
  | "contact_consent";
type Errors = Partial<Record<Field, string | null>>;

interface Form {
  consent: boolean;
  email: string;
  essence: string;
  forWhom: string;
  powiat: string;
  stage: string;
  title: string;
}

const emptyForm: Form = {
  consent: false,
  email: "",
  essence: "",
  forWhom: "",
  powiat: "",
  stage: "idea",
  title: "",
};

const validate = (form: Form): Errors => {
  const email = form.email.trim();
  return {
    contact_consent:
      email.length > 0 && !form.consent
        ? "Zaznacz zgodę, żeby ROPS mógł odpisać na ten adres."
        : null,
    contact_email: email.length > 0 && !isEmail(email) ? EMAIL_INVALID : null,
    essence:
      form.essence.trim().length < 20
        ? "Opisz pomysł w co najmniej 20 znakach."
        : null,
    for_whom:
      form.forWhom.trim().length < 3 ? "Napisz, dla kogo jest pomysł." : null,
    title:
      form.title.trim().length < 5
        ? "Nazwij pomysł w co najmniej 5 znakach."
        : null,
  };
};

export const useIdeaForm = () => {
  const [options, setOptions] = useState<IdeaOptions | null>(null);
  const [form, setForm] = useState<Form>(emptyForm);
  const [canvas, setCanvas] = useState<Partial<Canvas>>({});
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<IdeaCreated | null>(null);
  const [round, setRound] = useState(0);
  const params = useLocalSearchParams<{ problem?: string }>();
  const [problem, setProblem] = useState<{ id: string; title: string } | null>(
    null
  );

  useEffect(() => {
    const id = params.problem;
    if (!id) {
      setProblem(null);
      return;
    }
    const abort = new AbortController();
    api
      .problem(id, abort.signal)
      .then((found) => setProblem({ id: found.id, title: found.title }))
      .catch(() => setProblem(null));
    return () => abort.abort();
  }, [params.problem]);

  useEffect(() => {
    const abort = new AbortController();
    api
      .ideaOptions(abort.signal)
      .then(setOptions)
      .catch(() => setOptions(null));
    return () => abort.abort();
  }, []);

  const set = (patch: Partial<Form>) =>
    setForm((current) => ({ ...current, ...patch }));

  const submit = async () => {
    const problems = validate(form);
    setErrors(problems);
    if (Object.values(problems).some(Boolean)) {
      return;
    }
    const email = form.email.trim();
    setBusy(true);
    setError(null);
    try {
      const result = await api.createIdea({
        ...(problem ? { problem_id: problem.id } : {}),
        essence: form.essence.trim(),
        for_whom: form.forWhom.trim(),
        stage: form.stage,
        title: form.title.trim(),
        ...(Object.keys(canvas).length > 0 ? { canvas } : {}),
        ...(form.powiat ? { powiat: form.powiat } : {}),
        ...(email ? { contact_consent: true, contact_email: email } : {}),
      });
      await saveIdea({
        createdAt: new Date().toISOString(),
        id: result.id,
        number: result.number,
        title: form.title.trim(),
        token: result.edit_token,
      }).catch(() => undefined);
      setCreated(result);
    } catch (caught) {
      if (caught instanceof ApiError) {
        const next: Errors = {};
        for (const field of caught.fields) {
          next[field.field as Field] = field.message;
        }
        setErrors(next);
      }
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setForm(emptyForm);
    setCanvas({});
    setCreated(null);
    setErrors({});
    setRound((value) => value + 1);
  };

  const draft = {
    essence: form.essence.trim() || undefined,
    for_whom: form.forWhom.trim() || undefined,
    stage: form.stage,
    title: form.title.trim() || undefined,
  };

  const stageOptions: SelectOption[] = (options?.stages ?? []).map((item) => ({
    label: item.name,
    value: item.slug,
  }));

  const clearProblem = () => {
    setProblem(null);
    router.setParams({ problem: "" });
  };

  return {
    busy,
    canvas,
    clearProblem,
    created,
    draft,
    error,
    errors,
    form,
    needsConsent: form.email.trim().length > 0,
    options,
    problem,
    reset,
    round,
    set,
    setCanvas,
    stageOptions,
    submit,
  };
};

export const useIdeaAssistant = (
  draft: IdeaDraft,
  canvas: Partial<Canvas>,
  onCanvas: (canvas: Partial<Canvas>) => void
) => {
  const [result, setResult] = useState<AssistOut | null>(null);
  const [answers, setAnswers] = useState<AssistAnswer[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    const fresh = (result?.questions ?? [])
      .map((item) => ({
        answer: (drafts[item.question] ?? "").trim(),
        field: item.field,
        question: item.question,
      }))
      .filter((item) => item.answer.length > 0);
    const merged = { ...canvas };
    for (const item of fresh) {
      merged[item.field] = item.answer;
    }
    const nextAnswers = [
      ...answers,
      ...fresh.map((item) => ({
        answer: item.answer,
        question: item.question,
      })),
    ];
    setBusy(true);
    setError(null);
    try {
      const response = await api.assist(
        { ...draft, canvas: merged },
        nextAnswers
      );
      setAnswers(nextAnswers);
      setDrafts({});
      setResult(response);
      onCanvas(response.canvas);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const answer = (question: string, value: string) =>
    setDrafts((current) => ({ ...current, [question]: value }));

  return { answer, busy, drafts, error, result, run };
};
