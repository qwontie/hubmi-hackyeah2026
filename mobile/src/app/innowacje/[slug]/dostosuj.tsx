import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { ArrowLeft, FileText } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { InstitutionType, Powiat } from "@/api/types";
import { APP_NAME } from "@/config";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

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
      ? "Opisz swoją sytuację w co najmniej 20 znakach: kim są odbiorcy, jaki macie zespół i budżet."
      : null,
  institution: institution ? null : "Wybierz rodzaj instytucji.",
  place:
    place.length < 2 ? "Wpisz gminę, miejscowość albo nazwę instytucji." : null,
});

const fieldErrors = (caught: unknown): Partial<FormErrors> => {
  if (!(caught instanceof ApiError)) {
    return {};
  }
  const find = (name: string) =>
    caught.fields.find((field) => field.field === name)?.message ?? null;
  return {
    context: find("context"),
    institution: find("institution_type"),
    place: find("place"),
  };
};

export default function AdaptScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [title, setTitle] = useState<string | null>(null);
  const [types, setTypes] = useState<InstitutionType[]>([]);
  const [powiats, setPowiats] = useState<Powiat[]>([]);
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
    api
      .powiats(abort.signal)
      .then(setPowiats)
      .catch(() => setPowiats([]));
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
      if (caught instanceof Error && caught.name === "AbortError") {
        return;
      }
      setErrors({ ...noErrors, ...fieldErrors(caught) });
      setError(errorMessage(caught));
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Head>
        <title>{`Dostosuj rozwiązanie · ${APP_NAME}`}</title>
      </Head>
      <View>
        <Button
          icon={ArrowLeft}
          label="Wróć do opisu"
          onPress={() =>
            router.canGoBack() ? router.back() : router.replace("/biblioteka")
          }
          variant="quiet"
        />
      </View>
      <Sheet raised>
        <View style={styles.group}>
          <Heading level={1}>Plan usługi dla Twojej instytucji</Heading>
          {title ? (
            <Txt tone="soft" variant="lead">
              Na podstawie rozwiązania „{title}”.
            </Txt>
          ) : null}
        </View>
        {types.length > 0 ? (
          <Select
            emptyLabel="Wybierz"
            error={errors.institution}
            label="Rodzaj instytucji"
            onChange={setInstitution}
            options={types.map((item) => ({
              label: item.name,
              value: item.slug,
            }))}
            value={institution}
          />
        ) : null}
        <TextField
          error={errors.place}
          label="Gmina, miejscowość albo nazwa instytucji"
          maxLength={120}
          onChangeText={setPlace}
          placeholder="Na przykład: Gmina Wieliczka"
          value={place}
        />
        {powiats.length > 0 ? (
          <Select
            emptyLabel="Nie wybieram"
            label="Powiat"
            onChange={setPowiat}
            optional
            options={powiats.map((item) => ({
              label: item.name,
              value: item.slug,
            }))}
            value={powiat}
          />
        ) : null}
        <TextField
          error={errors.context}
          hint="Kim są Wasi odbiorcy, jaki macie zespół i budżet. Bez danych osobowych: plan można udostępnić linkiem."
          label="Opisz swoją sytuację"
          maxLength={3000}
          multiline
          onChangeText={setContext}
          value={context}
        />
        {error ? <Notice tone="error">{error}</Notice> : null}
        <Button
          busy={busy}
          icon={FileText}
          label={busy ? "Przygotowuję plan…" : "Przygotuj plan"}
          onPress={submit}
          size="large"
          variant="primary"
        />
        <View aria-live="polite">
          {busy ? (
            <Txt tone="soft">
              Układamy plan na podstawie opisu innowacji. To trwa do 10 sekund.
            </Txt>
          ) : null}
        </View>
      </Sheet>
    </Screen>
  );
}

const styles = StyleSheet.create({
  group: {
    gap: space.md,
  },
});
