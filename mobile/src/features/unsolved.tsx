import { Link } from "expo-router";
import { ArrowRight, Check, CircleAlert } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import {
  Pressable,
  StyleSheet,
  type Text,
  TextInput,
  View,
} from "react-native";
import { PowiatPicker } from "@/features/powiat-picker";
import { Stamp } from "@/features/stamp";
import type { RegistrationForm } from "@/hooks/use-match";
import { usePowiats } from "@/hooks/use-powiats";
import { focusElement } from "@/lib/a11y";
import { useTheme } from "@/theme/settings";
import { fonts, minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { nightAttr } from "@/ui/night";
import { Heading, Txt } from "@/ui/text";

export interface Registration {
  busy: boolean;
  error: string | null;
  fields: RegistrationForm;
  need: { at: Date; number: number | null } | null;
}

const EMAIL_ID = "unsolved-email";

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

function Step({ registration }: { registration: Registration }) {
  const { colors, lineHeight, type, wide } = useTheme();
  const powiats = usePowiats();
  const [focused, setFocused] = useState(false);
  const title = useRef<Text>(null);
  const { busy, error, fields } = registration;
  useEffect(() => {
    focusElement(title.current);
  }, []);
  return (
    <>
      <View style={styles.text}>
        <Heading level={2} night ref={title}>
          Przekaż problem do ROPS
        </Heading>
        <Txt tone="onNightSoft" variant="lead">
          Wyślemy Twój opis pracownikom ROPS. Wskaż powiat, a jeśli chcesz
          dostać odpowiedź, zostaw e-mail.
        </Txt>
      </View>
      <View style={[styles.form, wide && styles.formWide]}>
        <View style={[styles.column, wide && styles.columnWide]}>
          {powiats.options.length > 0 ? (
            <PowiatPicker
              onChange={fields.setPowiat}
              options={powiats.options}
              value={fields.powiat}
            />
          ) : null}
          <Problem text={fields.errors.powiat} />
        </View>
        <View style={[styles.column, wide && styles.columnWide]}>
          <Txt nativeID={EMAIL_ID} tone="onNight" variant="label" weight="600">
            E-mail
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
            placeholderTextColor="rgba(218, 219, 252, 0.72)"
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
      <Problem text={error} />
      <View style={styles.actions}>
        <Button
          busy={busy}
          fill={!wide}
          label={busy ? "Wysyłam" : "Wyślij do ROPS"}
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

export function Unsolved({ registration }: { registration: Registration }) {
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
          Żadne z tych rozwiązań nie pomaga?
        </Heading>
        <Txt tone="onNightSoft" variant="lead">
          Przekaż swój problem do ROPS. Pracownik ROPS przeczyta go i odpowie.
        </Txt>
      </View>
      <Button
        fill={!wide}
        label="Mój problem nie został rozwiązany"
        onPress={() => fields.setOpen(true)}
        ref={opener}
        size="large"
        variant="light"
      />
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
            ROPS przyjął Twoje zgłoszenie
          </Heading>
          <Txt tone="onNightSoft" variant="lead">
            Pracownik ROPS przeczyta opis. Odpowiedź znajdziesz w zakładce
            Zgłoszenia.
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
