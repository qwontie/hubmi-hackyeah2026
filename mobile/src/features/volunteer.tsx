import { Check, HandHeart, Send } from "lucide-react-native";
import { useId } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { PowiatField } from "@/features/powiat-field";
import { Trap } from "@/features/trap";
import { TESTER_ROLES } from "@/hooks/use-tester";
import { useVolunteer } from "@/hooks/use-volunteer";
import type { SelectOption } from "@/lib/options";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Heading, Txt } from "@/ui/text";

export function ChoiceGrid({
  error,
  label,
  onChange,
  options,
  value,
}: {
  error?: string | null;
  label: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  value: string | null;
}) {
  const { colors, highContrast, wide } = useTheme();
  const labelId = useId();
  return (
    <View style={styles.block}>
      <Txt nativeID={labelId} variant="label" weight="600">
        {label}
      </Txt>
      <View
        aria-invalid={error ? true : undefined}
        aria-labelledby={labelId}
        role="radiogroup"
        style={styles.choices}
      >
        {options.map((option) => {
          const checked = option.value === value;
          return (
            <Pressable
              aria-checked={checked}
              key={option.value}
              onPress={() => onChange(option.value)}
              role="radio"
              style={[
                styles.choice,
                wide && styles.choiceWide,
                {
                  backgroundColor: checked ? colors.tone : colors.sunk,
                  borderColor:
                    checked || highContrast ? colors.stamp : colors.ruleStrong,
                  borderWidth: checked || highContrast ? 2 : 1.5,
                },
              ]}
            >
              <View
                style={[
                  styles.mark,
                  {
                    backgroundColor: checked ? colors.stamp : "transparent",
                    borderColor: checked ? colors.stamp : colors.ruleStrong,
                  },
                ]}
              >
                {checked ? (
                  <Check
                    aria-hidden
                    color={colors.onStamp}
                    size={16}
                    strokeWidth={3}
                  />
                ) : null}
              </View>
              <Txt style={styles.grow} variant="label" weight="500">
                {option.label}
              </Txt>
            </Pressable>
          );
        })}
      </View>
      {error ? (
        <Txt role="alert" tone="bad" weight="500">
          {error}
        </Txt>
      ) : null}
    </View>
  );
}

function VolunteerForm({
  onCancel,
  volunteer,
}: {
  onCancel: () => void;
  volunteer: ReturnType<typeof useVolunteer>;
}) {
  return (
    <View style={styles.block}>
      <ChoiceGrid
        label="Kim jesteś?"
        onChange={(value) => volunteer.setWho(value as typeof volunteer.who)}
        options={TESTER_ROLES}
        value={volunteer.who}
      />
      {volunteer.needsOrganization ? (
        <TextField
          label="Nazwa organizacji lub instytucji"
          onChangeText={volunteer.setOrganization}
          value={volunteer.organization}
        />
      ) : null}
      <PowiatField
        error={volunteer.errors.powiat}
        onChange={volunteer.setPowiat}
        value={volunteer.powiat}
      />
      <TextField
        error={volunteer.errors.proposal}
        hint="Kilka zdań: z kim, gdzie i jak chcesz wypróbować to rozwiązanie."
        label="Co chcesz zrobić?"
        multiline
        onChangeText={volunteer.setProposal}
        value={volunteer.proposal}
      />
      <TextField
        autoCapitalize="none"
        autoComplete="email"
        error={volunteer.errors.email}
        hint="Pracownik ROPS odpisze na ten adres."
        inputMode="email"
        keyboardType="email-address"
        label="Twój adres e-mail"
        onChangeText={volunteer.setEmail}
        textContentType="emailAddress"
        value={volunteer.email}
      />
      <Checkbox
        checked={volunteer.consent}
        error={volunteer.errors.consent}
        label="Zgadzam się, żeby ROPS w Krakowie użył mojego adresu e-mail do kontaktu w sprawie wolontariatu przy tym rozwiązaniu."
        onChange={volunteer.setConsent}
      />
      <Trap onChange={volunteer.setWebsite} value={volunteer.website} />
      {volunteer.error ? <Notice tone="error">{volunteer.error}</Notice> : null}
      <View style={styles.row}>
        <Button
          busy={volunteer.busy}
          icon={Send}
          label={volunteer.busy ? "Wysyłam" : "Wyślij zgłoszenie"}
          onPress={volunteer.submit}
          variant="primary"
        />
        <Button label="Anuluj" onPress={onCancel} variant="quiet" />
      </View>
    </View>
  );
}

const PROMISE =
  "Pracownik ROPS czyta każde zgłoszenie i odpisuje na podany adres.";

function Sent({ done }: { done: { duplicate: boolean; email: string } }) {
  return (
    <Notice
      title={
        done.duplicate
          ? "Masz już zgłoszenie do tego rozwiązania"
          : "Zgłoszenie trafiło do ROPS"
      }
      tone="success"
    >
      {`Pracownik ROPS przeczyta je i odpisze na adres ${done.email}. Potwierdzenie wysłaliśmy e-mailem.`}
    </Notice>
  );
}

export function VolunteerBlock({ slug }: { slug: string }) {
  const volunteer = useVolunteer(slug);
  const { done, open } = volunteer;
  return (
    <View style={styles.block}>
      <Heading level={2}>Zostań wolontariuszem</Heading>
      <Txt>
        Możesz wypróbować to rozwiązanie w praktyce, na przykład w klubie
        seniora, szkole albo swojej organizacji. Napisz, co chcesz zrobić.{" "}
        {PROMISE}
      </Txt>
      {done ? <Sent done={done} /> : null}
      {!done && open ? (
        <VolunteerForm
          onCancel={() => volunteer.setOpen(false)}
          volunteer={volunteer}
        />
      ) : null}
      {done || open ? null : (
        <Button
          icon={HandHeart}
          label="Zostań wolontariuszem"
          onPress={() => volunteer.setOpen(true)}
        />
      )}
    </View>
  );
}

export function VolunteerApply({
  onCancel,
  slug,
}: {
  onCancel: () => void;
  slug: string;
}) {
  const volunteer = useVolunteer(slug, true);
  return volunteer.done ? (
    <Sent done={volunteer.done} />
  ) : (
    <VolunteerForm onCancel={onCancel} volunteer={volunteer} />
  );
}

const styles = StyleSheet.create({
  block: {
    gap: space.md,
  },
  choice: {
    alignItems: "center",
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget + 8,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
    width: "100%",
  },
  choices: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  choiceWide: {
    flexBasis: "40%",
    flexGrow: 1,
    width: "auto",
  },
  grow: {
    flex: 1,
  },
  mark: {
    alignItems: "center",
    borderRadius: radius.pill,
    borderWidth: 2,
    height: 24,
    justifyContent: "center",
    width: 24,
  },
  row: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
});
