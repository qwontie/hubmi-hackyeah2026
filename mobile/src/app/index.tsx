import { RotateCcw, Search } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { TEXT_MAX } from "@/config";
import { MatchResults } from "@/features/match-results";
import { VoiceInput } from "@/features/voice-input";
import { charactersLeft, useMatch } from "@/hooks/use-match";
import { usePowiats } from "@/hooks/use-powiats";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const TITLE_ID = "problem-title";

function CharactersLeft({ length }: { length: number }) {
  const left = charactersLeft(length);
  if (!left) {
    return null;
  }
  return (
    <Txt aria-live="polite" tone={left.over ? "bad" : "soft"} variant="small">
      {left.text}
    </Txt>
  );
}

export default function MatchScreen() {
  const { wide } = useTheme();
  const powiats = usePowiats();
  const {
    blocked,
    fieldError,
    inputRef,
    loading,
    powiat,
    recognition,
    reset,
    resultsRef,
    setPowiat,
    setText,
    state,
    submit,
    text,
  } = useMatch();

  return (
    <Screen>
      <Sheet raised>
        <View style={styles.intro}>
          <Heading level={1} nativeID={TITLE_ID}>
            Opisz problem
          </Heading>
          <Txt tone="soft" variant="lead">
            Napisz zwykłymi słowami, z czym potrzebujesz pomocy. Pokażemy
            sprawdzone rozwiązania z biblioteki innowacji ROPS w Krakowie.
          </Txt>
        </View>

        <View style={styles.field}>
          <TextField
            error={fieldError}
            label="Opisz problem"
            labelledBy={TITLE_ID}
            large
            maxLength={TEXT_MAX + 200}
            multiline
            onChangeText={setText}
            placeholder="Na przykład: mama ma demencję, wychodzi z domu i się gubi."
            ref={inputRef}
            value={text}
          />
          <CharactersLeft length={text.length} />
        </View>

        <VoiceInput recognition={recognition} />

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

        <View style={[styles.actions, wide && styles.actionsWide]}>
          <Button
            busy={loading}
            disabled={blocked}
            fill={!wide}
            icon={Search}
            label={loading ? "Szukam rozwiązań…" : "Znajdź rozwiązania"}
            onPress={submit}
            size="large"
            variant="primary"
          />
          {state.kind === "done" ? (
            <Button
              icon={RotateCcw}
              label="Opisz inny problem"
              onPress={reset}
              variant="quiet"
            />
          ) : null}
        </View>

        <View aria-live="polite">
          {loading ? (
            <Txt tone="soft">
              Szukamy w bibliotece ROPS. To trwa zwykle kilka sekund.
            </Txt>
          ) : null}
        </View>
      </Sheet>

      {state.kind === "error" ? (
        <Notice tone="error">
          <View style={styles.errorBody}>
            <Txt>{state.message}</Txt>
            {state.retryable ? (
              <Button label="Spróbuj ponownie" onPress={submit} />
            ) : null}
          </View>
        </Notice>
      ) : null}

      {state.kind === "done" ? (
        <MatchResults
          at={state.at}
          key={state.response.need.id}
          response={state.response}
          titleRef={resultsRef}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: {
    gap: space.md,
  },
  actionsWide: {
    alignItems: "center",
    flexDirection: "row",
  },
  errorBody: {
    gap: space.md,
  },
  field: {
    gap: space.sm,
  },
  intro: {
    gap: space.md,
  },
});
