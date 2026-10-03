import { MapPin, Send } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { DemoTag } from "@/features/demo-tag";
import { PowiatField } from "@/features/powiat-field";
import { Trap } from "@/features/trap";
import { demandWords, useDemand } from "@/hooks/use-demand";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Heading, Txt } from "@/ui/text";

export function DemandBlock({ slug }: { slug: string }) {
  const demand = useDemand(slug);
  const { count, done, open } = demand;
  return (
    <View style={styles.block}>
      <Heading level={2}>Chcesz tego u siebie?</Heading>
      <Txt>
        Takie rozwiązanie wprowadza gmina albo organizacja, nie jedna osoba. Daj
        znać ROPS, że przydałoby się w Twojej okolicy.
      </Txt>
      {count !== null && count > 0 ? (
        <View>
          <Txt tone="soft" weight="500">
            {demandWords(count)}
          </Txt>
          <DemoTag />
        </View>
      ) : null}
      {done ? (
        <Notice
          title={
            done.duplicate ? "Twój głos już mamy" : "Zapisaliśmy Twój głos"
          }
          tone="success"
        >
          ROPS widzi, w którym powiecie mieszkańcy chcą tego rozwiązania.
          Decyzję o wprowadzeniu podejmuje gmina albo organizacja.
        </Notice>
      ) : null}
      {!done && open ? (
        <>
          <PowiatField
            error={demand.errors.powiat}
            onChange={demand.setPowiat}
            value={demand.powiat}
          />
          <TextField
            autoCapitalize="none"
            autoComplete="email"
            error={demand.errors.email}
            hint="Nieobowiązkowo. Zostaw, jeśli ROPS może do Ciebie napisać w tej sprawie."
            inputMode="email"
            keyboardType="email-address"
            label="Twój adres e-mail"
            onChangeText={demand.setEmail}
            textContentType="emailAddress"
            value={demand.email}
          />
          {demand.email.trim() ? (
            <Checkbox
              checked={demand.consent}
              error={demand.errors.consent}
              label="Zgadzam się, żeby ROPS w Krakowie użył mojego adresu e-mail do kontaktu w sprawie tego rozwiązania."
              onChange={demand.setConsent}
            />
          ) : null}
          <Trap onChange={demand.setWebsite} value={demand.website} />
          {demand.error ? <Notice tone="error">{demand.error}</Notice> : null}
          <View style={styles.row}>
            <Button
              busy={demand.busy}
              icon={Send}
              label={demand.busy ? "Wysyłam" : "Wyślij"}
              onPress={demand.submit}
              variant="primary"
            />
            <Button
              label="Anuluj"
              onPress={() => demand.setOpen(false)}
              variant="quiet"
            />
          </View>
        </>
      ) : null}
      {done || open ? null : (
        <Button
          icon={MapPin}
          label="Chcę tego u siebie"
          onPress={() => demand.setOpen(true)}
          variant="primary"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  block: {
    gap: space.md,
  },
  row: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
});
