import { Link } from "expo-router";
import { ArrowRight, Check, CircleAlert, MapPin, X } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import {
  Pressable,
  StyleSheet,
  type Text,
  TextInput,
  View,
} from "react-native";
import { TEXT_MAX } from "@/config";
import { Stamp } from "@/features/stamp";
import { Trap } from "@/features/trap";
import type { RegistrationForm } from "@/hooks/use-match";
import { usePowiats } from "@/hooks/use-powiats";
import { focusElement } from "@/lib/a11y";
import { fold } from "@/lib/crisis";
import type { SelectOption } from "@/lib/options";
import { useTheme } from "@/theme/settings";
import { fonts, minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { nightAttr } from "@/ui/night";
import { Heading, Txt } from "@/ui/text";

export interface Registration {
  busy: boolean;
  error: string | null;
  fields: RegistrationForm;
  need: { at: Date; duplicate?: boolean; number: number | null } | null;
}

const EMAIL_ID = "unsolved-email";
const POWIAT_ID = "unsolved-powiat";
const SHOWN = 5;
const ROW_HOVER = "rgba(252, 252, 255, 0.12)";
const TEXT_ID = "unsolved-text";
const HINT = "rgba(218, 219, 252, 0.72)";

function Problem({ text }: { text: string | null }) {
  const { colors } = useTheme();
  if (!text) {
    return null;
  }
  return (
    <View style={styles.problem}>
      <CircleAlert aria-hidden color={colors.onNight} size={24} />
      <Txt style={styles.grow} tone="onNight" weight="600">
        {text}
      </Txt>
    </View>
  );
}

function Consent({ fields }: { fields: RegistrationForm }) {
  const { colors } = useTheme();
  return (
    <Pressable
      aria-checked={fields.consent}
      onPress={() => fields.setConsent(!fields.consent)}
      role="checkbox"
      style={styles.consent}
    >
      <View
        style={[
          styles.box,
          {
            backgroundColor: fields.consent ? colors.onNight : "transparent",
            borderColor: colors.onNight,
          },
        ]}
      >
        {fields.consent ? (
          <Check aria-hidden color={colors.night} size={20} strokeWidth={3} />
        ) : null}
      </View>
      <Txt style={styles.grow} tone="onNight" variant="label">
        Zgadzam się, żeby ROPS w Krakowie użył tego adresu tylko do odpowiedzi
        na moje zgłoszenie.
      </Txt>
    </Pressable>
  );
}

function PowiatMatch({
  label,
  onPress,
}: {
  label: string;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const [hovered, setHovered] = useState(false);
  return (
    <Pressable
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={onPress}
      role="button"
      style={[
        styles.match,
        {
          backgroundColor: hovered ? ROW_HOVER : "transparent",
          borderBottomColor: colors.glassNightEdge,
        },
      ]}
    >
      <MapPin aria-hidden color={colors.onNightSoft} size={20} />
      <Txt style={styles.grow} tone="onNight" variant="label" weight="600">
        {label}
      </Txt>
    </Pressable>
  );
}

function PowiatChoice({
  onChange,
  options,
  value,
}: {
  onChange: (slug: string) => void;
  options: SelectOption[];
  value: string;
}) {
  const { colors, lineHeight, type } = useTheme();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const input = useRef<TextInput>(null);
  const cleared = useRef(false);
  const chosen = options.find((option) => option.value === value);

  useEffect(() => {
    if (!chosen && cleared.current) {
      cleared.current = false;
      input.current?.focus();
    }
  }, [chosen]);

  const wanted = fold(query.trim());
  const matches = wanted
    ? options
        .filter((option) => fold(option.label).includes(wanted))
        .slice(0, SHOWN)
    : [];
  const pick = (slug: string) => {
    setQuery("");
    onChange(slug);
  };

  return (
    <View style={styles.column}>
      <Txt nativeID={POWIAT_ID} tone="onNight" variant="label" weight="600">
        Powiat
        <Txt tone="onNightSoft" variant="label">
          {" "}
          (nieobowiązkowo)
        </Txt>
      </Txt>
      {chosen ? (
        <View style={styles.chosen}>
          <Check aria-hidden color={colors.onNight} size={22} />
          <Txt style={styles.grow} tone="onNight" variant="lead" weight="600">
            {chosen.label}
          </Txt>
          <Pressable
            aria-label={`Usuń wybór: ${chosen.label}`}
            onPress={() => {
              cleared.current = true;
              onChange("");
            }}
            role="button"
            style={styles.clear}
          >
            <X aria-hidden color={colors.onNight} size={22} />
          </Pressable>
        </View>
      ) : (
        <>
          <TextInput
            aria-labelledby={POWIAT_ID}
            autoComplete="off"
            autoCorrect={false}
            onBlur={() => setFocused(false)}
            onChangeText={setQuery}
            onFocus={() => setFocused(true)}
            onSubmitEditing={() => {
              const [first] = matches;
              if (first) {
                pick(first.value);
              }
            }}
            placeholder="Wpisz nazwę, np. Tarnów"
            placeholderTextColor={HINT}
            ref={input}
            selectionColor={colors.onNightSoft}
            style={[
              styles.input,
              {
                borderBottomColor: focused
                  ? colors.onNight
                  : colors.glassNightEdge,
                color: colors.onNight,
                fontFamily: fonts["500"],
                fontSize: type.lead,
                lineHeight: lineHeight(type.lead),
              },
            ]}
            value={query}
          />
          {wanted ? (
            <View aria-label="Pasujące powiaty" role="list">
              {matches.map((option) => (
                <PowiatMatch
                  key={option.value}
                  label={option.label}
                  onPress={() => pick(option.value)}
                />
              ))}
              {matches.length === 0 ? (
                <Txt tone="onNightSoft" variant="label">
                  Nie ma takiego powiatu w Małopolsce.
                </Txt>
              ) : null}
            </View>
          ) : null}
        </>
      )}
    </View>
  );
}

function Step({ registration }: { registration: Registration }) {
  const { colors, lineHeight, type, wide } = useTheme();
  const powiats = usePowiats();
  const [focused, setFocused] = useState(false);
  const [textFocused, setTextFocused] = useState(false);
  const [textHeight, setTextHeight] = useState(0);
  const title = useRef<Text>(null);
  const { busy, error, fields } = registration;
  useEffect(() => {
    focusElement(title.current);
  }, []);
  return (
    <>
      <View style={styles.text}>
        <Heading level={2} night ref={title}>
          Zgłoś problem do ROPS
        </Heading>
        <Txt tone="onNightSoft" variant="lead">
          Wyślemy Twój opis pracownikom ROPS. Możesz go jeszcze poprawić.
        </Txt>
      </View>
      <View style={styles.column}>
        <Txt nativeID={TEXT_ID} tone="onNight" variant="label" weight="600">
          Twój opis
        </Txt>
        <TextInput
          aria-invalid={fields.errors.text ? true : undefined}
          aria-labelledby={TEXT_ID}
          maxLength={TEXT_MAX + 200}
          multiline
          onBlur={() => setTextFocused(false)}
          onChangeText={fields.setText}
          onContentSizeChange={(event) => {
            const next = Math.ceil(event.nativeEvent.contentSize.height);
            setTextHeight((current) => (next > current ? next : current));
          }}
          onFocus={() => setTextFocused(true)}
          selectionColor={colors.onNightSoft}
          style={[
            styles.input,
            {
              borderBottomColor: textFocused
                ? colors.onNight
                : colors.glassNightEdge,
              color: colors.onNight,
              fontFamily: fonts["500"],
              fontSize: type.lead,
              height: Math.max(minTarget + 4, textHeight),
              lineHeight: lineHeight(type.lead),
            },
          ]}
          value={fields.text}
        />
        <Problem text={fields.errors.text} />
      </View>
      <View style={[styles.form, wide && styles.formWide]}>
        <View style={[styles.column, wide && styles.columnWide]}>
          {powiats.options.length > 0 ? (
            <PowiatChoice
              onChange={fields.setPowiat}
              options={powiats.options}
              value={fields.powiat}
            />
          ) : null}
          <Problem text={fields.errors.powiat} />
        </View>
        <View style={[styles.column, wide && styles.columnWide]}>
          <Txt nativeID={EMAIL_ID} tone="onNight" variant="label" weight="600">
            E-mail, na który ROPS może odpisać
            <Txt tone="onNightSoft" variant="label">
              {" "}
              (nieobowiązkowo)
            </Txt>
          </Txt>
          <TextInput
            aria-invalid={fields.errors.email ? true : undefined}
            aria-labelledby={EMAIL_ID}
            autoCapitalize="none"
            autoComplete="email"
            inputMode="email"
            onBlur={() => setFocused(false)}
            onChangeText={fields.setEmail}
            onFocus={() => setFocused(true)}
            placeholder="np. anna@example.org"
            placeholderTextColor={HINT}
            selectionColor={colors.onNightSoft}
            style={[
              styles.input,
              {
                borderBottomColor: focused
                  ? colors.onNight
                  : colors.glassNightEdge,
                color: colors.onNight,
                fontFamily: fonts["500"],
                fontSize: type.lead,
                lineHeight: lineHeight(type.lead),
              },
            ]}
            value={fields.email}
          />
          <Problem text={fields.errors.email} />
          {fields.email.trim().length > 0 ? <Consent fields={fields} /> : null}
          <Problem text={fields.errors.consent} />
        </View>
      </View>
      <Trap onChange={fields.setWebsite} value={fields.website} />
      <Problem text={error} />
      <View style={styles.actions}>
        <Button
          busy={busy}
          fill={!wide}
          label={busy ? "Wysyłam" : "Wyślij zgłoszenie"}
          onPress={() => {
            fields.submit().catch(() => undefined);
          }}
          size="large"
          variant="light"
        />
        <Pressable
          onPress={() => fields.setOpen(false)}
          role="button"
          style={styles.cancel}
        >
          <Txt tone="onNight" variant="label" weight="600">
            Anuluj
          </Txt>
        </Pressable>
      </View>
    </>
  );
}

export function Unsolved({
  empty = false,
  onEdit,
  registration,
}: {
  empty?: boolean;
  onEdit?: () => void;
  registration: Registration;
}) {
  const { colors, wide } = useTheme();
  const { fields, need } = registration;
  const opener = useRef<View>(null);
  const doneTitle = useRef<Text>(null);
  const wasOpen = useRef<boolean>(false);
  const accepted = Boolean(need);

  useEffect(() => {
    if (accepted) {
      if (wasOpen.current) {
        focusElement(doneTitle.current);
      }
    } else if (wasOpen.current && !fields.open) {
      focusElement(opener.current);
    }
    wasOpen.current = fields.open;
  }, [accepted, fields.open]);

  let body = (
    <>
      <View style={styles.text}>
        <Heading level={2} night>
          {empty
            ? "Zgłoś ten problem do ROPS"
            : "Żadne z tych rozwiązań nie pomaga?"}
        </Heading>
        <Txt tone="onNightSoft" variant="lead">
          {empty
            ? "Pracownik ROPS przeczyta Twój opis. Jeśli zostawisz e-mail, może odpisać."
            : "Zgłoś swój problem do ROPS. Pracownik ROPS go przeczyta. Jeśli zostawisz e-mail, może odpisać."}
        </Txt>
      </View>
      <View style={styles.actions}>
        <Button
          fill={!wide}
          label="Zgłoś problem"
          onPress={() => fields.setOpen(true)}
          ref={opener}
          size="large"
          variant="light"
        />
        {empty && onEdit ? (
          <Pressable onPress={onEdit} role="button" style={styles.cancel}>
            <Txt tone="onNight" variant="label" weight="600">
              Popraw opis
            </Txt>
          </Pressable>
        ) : null}
      </View>
    </>
  );
  if (fields.open) {
    body = <Step registration={registration} />;
  }
  if (need) {
    body = (
      <View style={[styles.done, wide && styles.doneWide]}>
        <Stamp at={need.at} number={need.number} word="PRZYJĘTO" />
        <View style={[styles.text, wide && styles.textWide]}>
          <Heading level={2} night ref={doneTitle}>
            {need.duplicate
              ? "ROPS ma już to zgłoszenie"
              : "ROPS przyjął Twoje zgłoszenie"}
          </Heading>
          <Txt tone="onNightSoft" variant="lead">
            Pracownik ROPS przeczyta opis. Jeśli odpisze, odpowiedź znajdziesz w
            zakładce Zgłoszenia. W pilnej sprawie zwróć się do ośrodka pomocy
            społecznej w swojej gminie.
          </Txt>
          <Link asChild href="/zgloszenia">
            <Pressable role="link" style={styles.link}>
              <Txt tone="onNight" variant="label" weight="600">
                Przejdź do zgłoszeń
              </Txt>
              <ArrowRight aria-hidden color={colors.onNight} size={22} />
            </Pressable>
          </Link>
        </View>
      </View>
    );
  }

  return (
    <View
      aria-live="polite"
      style={[styles.block, { backgroundColor: colors.night }]}
      {...nightAttr(true)}
    >
      {body}
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.lg,
  },
  block: {
    borderRadius: radius.sheet,
    gap: space.xl,
    padding: space.xl,
  },
  box: {
    alignItems: "center",
    borderRadius: 10,
    borderWidth: 2,
    height: 30,
    justifyContent: "center",
    width: 30,
  },
  cancel: {
    justifyContent: "center",
    minHeight: minTarget,
    paddingHorizontal: space.md,
  },
  chosen: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm + 2,
    minHeight: minTarget + 4,
  },
  clear: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: minTarget,
    justifyContent: "center",
    width: minTarget,
  },
  column: {
    gap: space.md,
  },
  columnWide: {
    flex: 1,
  },
  consent: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget,
    paddingVertical: space.xs,
  },
  done: {
    gap: space.xl,
  },
  doneWide: {
    alignItems: "center",
    flexDirection: "row",
  },
  form: {
    gap: space.xl,
  },
  formWide: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.xxl,
  },
  grow: {
    flex: 1,
  },
  input: {
    borderBottomWidth: 2,
    minHeight: minTarget + 4,
    paddingBottom: space.sm,
    paddingHorizontal: 0,
  },
  link: {
    alignItems: "center",
    alignSelf: "flex-start",
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
  },
  match: {
    alignItems: "center",
    borderBottomWidth: 1,
    flexDirection: "row",
    gap: space.sm + 2,
    minHeight: minTarget + 4,
    paddingHorizontal: space.xs,
  },
  problem: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.sm + 2,
  },
  text: {
    gap: space.sm + 2,
  },
  textWide: {
    flex: 1,
  },
});
