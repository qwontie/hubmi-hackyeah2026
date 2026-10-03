import { router } from "expo-router";
import Head from "expo-router/head";
import { Mail, MessageSquareText, PenLine, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { ContactForm } from "@/features/contact-form";
import { Stamp } from "@/features/stamp";
import { formatDate } from "@/lib/plural";
import { forgetNeed, type StoredNeed, useStoredNeeds } from "@/storage/needs";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Txt } from "@/ui/text";

function NeedEntry({ need, last }: { need: StoredNeed; last: boolean }) {
  const { colors, wide } = useTheme();
  const [adding, setAdding] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [confirmForget, setConfirmForget] = useState(false);
  const meta = [
    need.number ? null : `wysłane ${formatDate(need.createdAt)}`,
    need.clusterTitle ? `temat: ${need.clusterTitle}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <View
      role="listitem"
      style={[
        styles.entry,
        { borderBottomColor: colors.rule, borderBottomWidth: last ? 0 : 1 },
      ]}
    >
      <Txt variant="lead" weight="500">
        {need.text || "Zgłoszenie otwarte z linku od ROPS."}
      </Txt>
      {need.number ? (
        <Stamp
          at={new Date(need.createdAt)}
          number={need.number}
          word="PRZYJĘTO"
        />
      ) : null}
      {meta ? (
        <Txt tone="soft" variant="detail">
          {meta}
        </Txt>
      ) : null}
      {need.contactEmail ? (
        <Txt tone="soft">Odpowiedź przyjdzie na adres {need.contactEmail}.</Txt>
      ) : null}
      {need.nothingFits ? (
        <Txt tone="soft">Zaznaczono, że żadna propozycja nie pasuje.</Txt>
      ) : null}
      {saved ? (
        <Notice tone="success">{`Zapisaliśmy adres ${saved}. ROPS odpisze na niego.`}</Notice>
      ) : null}
      {adding && !need.contactEmail ? (
        <ContactForm
          needId={need.id}
          nothingFits={false}
          onDone={(email) => {
            setAdding(false);
            setSaved(email);
          }}
          requireEmail
          submitLabel="Zapisz adres"
          token={need.token}
        />
      ) : null}
      <View style={styles.actions}>
        <Button
          fill={!wide}
          icon={MessageSquareText}
          label="Rozmowa z ROPS"
          onPress={() =>
            router.push({
              params: { id: need.id },
              pathname: "/zgloszenie/[id]",
            })
          }
          variant="primary"
        />
        {need.contactEmail || adding ? null : (
          <Button
            fill={!wide}
            icon={Mail}
            label="Chcę odpowiedź e-mailem"
            onPress={() => setAdding(true)}
          />
        )}
        {confirmForget ? (
          <View style={styles.confirm}>
            <Txt>
              Usunąć to zgłoszenie z tego urządzenia? ROPS nadal je widzi.
            </Txt>
            <View style={styles.actions}>
              <Button
                icon={Trash2}
                label="Tak, usuń z urządzenia"
                onPress={() => {
                  forgetNeed(need.id).catch(() => undefined);
                }}
              />
              <Button
                label="Anuluj"
                onPress={() => setConfirmForget(false)}
                variant="quiet"
              />
            </View>
          </View>
        ) : (
          <Button
            icon={Trash2}
            label="Usuń z tego urządzenia"
            onPress={() => setConfirmForget(true)}
            variant="quiet"
          />
        )}
      </View>
    </View>
  );
}

export default function SubmissionsScreen() {
  const needs = useStoredNeeds();
  return (
    <Screen tabs title="Moje zgłoszenia">
      <Head>
        <title>{`Moje zgłoszenia · ${APP_NAME}`}</title>
      </Head>
      {needs === null ? null : (
        <Sheet>
          {needs.length === 0 ? (
            <View style={styles.empty}>
              <Txt>Nie masz jeszcze zgłoszeń na tym urządzeniu.</Txt>
              <Button
                icon={PenLine}
                label="Opisz problem"
                onPress={() => router.navigate("/")}
                variant="primary"
              />
            </View>
          ) : (
            <View role="list">
              {needs.map((need, index) => (
                <NeedEntry
                  key={need.id}
                  last={index === needs.length - 1}
                  need={need}
                />
              ))}
            </View>
          )}
        </Sheet>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  confirm: {
    gap: space.md,
    width: "100%",
  },
  empty: {
    gap: space.lg,
  },
  entry: {
    gap: space.lg,
    paddingVertical: space.lg,
  },
  intro: {
    gap: space.md,
  },
});
