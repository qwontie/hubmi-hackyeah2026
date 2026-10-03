import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { ArrowLeft, FileText } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { useAdaptForm } from "@/hooks/use-adaptation";
import { usePowiats } from "@/hooks/use-powiats";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function AdaptScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const powiats = usePowiats();
  const {
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
  } = useAdaptForm(slug);

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
        {institutionOptions.length > 0 ? (
          <Select
            emptyLabel="Wybierz"
            error={errors.institution}
            label="Rodzaj instytucji"
            onChange={setInstitution}
            options={institutionOptions}
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
        {powiats.options.length > 0 ? (
          <Select
            emptyLabel="Nie wybieram"
            label="Powiat"
            onChange={setPowiat}
            optional
            options={powiats.options}
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
