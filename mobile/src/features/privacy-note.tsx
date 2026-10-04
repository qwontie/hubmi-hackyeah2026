import { Link } from "expo-router";
import { Txt } from "@/ui/text";

export const PRIVACY_PATH = "/prywatnosc";

export function PrivacyNote({
  night = false,
  text = "Dane z tego formularza trafią do ROPS w Krakowie.",
}: {
  night?: boolean;
  text?: string;
}) {
  const tone = night ? "onNightSoft" : "soft";
  return (
    <Txt tone={tone} variant="detail">
      {`${text} `}
      <Link asChild href={PRIVACY_PATH}>
        <Txt
          style={{ textDecorationLine: "underline" }}
          tone={night ? "onNight" : "stamp"}
          variant="detail"
          weight="600"
        >
          Jak chronimy Twoje dane
        </Txt>
      </Link>
    </Txt>
  );
}

export function OthersDataHint({ night = false }: { night?: boolean }) {
  return (
    <Txt tone={night ? "onNightSoft" : "soft"} variant="detail">
      Nie wpisuj imion, adresów ani informacji o zdrowiu innych osób.
    </Txt>
  );
}
