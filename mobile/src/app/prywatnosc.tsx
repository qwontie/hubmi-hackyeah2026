import Head from "expo-router/head";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { space } from "@/theme/tokens";
import { ExternalLink } from "@/ui/external-link";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const ROPS = "https://rops.krakow.pl";

const FORMS = [
  {
    data: "opis problemu i powiat, a jeśli chcesz odpowiedzi, także adres e-mail",
    name: "Zgłoszenie problemu",
    why: "żeby ROPS wiedział o problemie i mógł Ci odpisać",
  },
  {
    data: "powiat i, jeśli chcesz, adres e-mail",
    name: "„Chcę tego u siebie”",
    why: "żeby ROPS wiedział, gdzie dane rozwiązanie jest potrzebne",
  },
  {
    data: "kim jesteś, nazwa organizacji, co chcesz zrobić i adres e-mail, a potem Twoja relacja z działania",
    name: "Wolontariat",
    why: "żeby ROPS mógł się z Tobą umówić i wiedział, czy rozwiązanie działa",
  },
  {
    data: "opis pomysłu, powiat i adres e-mail",
    name: "Pomysł",
    why: "żeby ROPS mógł ocenić pomysł i porozmawiać z Tobą",
  },
  {
    data: "treść wniosku i adres e-mail",
    name: "Wniosek o grant",
    why: "żeby ROPS mógł rozpatrzyć wniosek i się z Tobą skontaktować",
  },
  {
    data: "adres e-mail",
    name: "Powiadomienia o naborach",
    why: "żeby wysłać Ci wiadomość o nowym naborze; wypiszesz się linkiem w każdej wiadomości",
  },
  {
    data: "treść porady",
    name: "Odpowiedź eksperta",
    why: "żeby przekazać ją osobie, która zgłosiła sprawę",
  },
  {
    data: "wiadomości, które piszesz, i adres e-mail, jeśli go podasz",
    name: "Rozmowa z ROPS przez link",
    why: "żeby prowadzić rozmowę o Twojej sprawie",
  },
];

const PROCESSORS = [
  "Google (Gemini API): dostaje tekst, który wpisujesz w wyszukiwanie, w zgłoszenie, w pomysł i w pomocników AI, żeby znaleźć pasujące rozwiązania i pomóc w opisie. Nie wysyłamy tam Twojego adresu e-mail.",
  "Resend: wysyła wiadomości e-mail, na przykład odpowiedź ROPS albo powiadomienie o naborze.",
  "Serwer w Unii Europejskiej przechowuje dane serwisu. Cloudflare chroni stronę przed atakami i przekazuje ruch.",
];

const DEVICE = [
  "ustawienia dostępności, na przykład rozmiar tekstu i kontrast;",
  "linki do Twoich zgłoszeń, pomysłów, wniosków i wolontariatu, żeby wrócić do nich bez zakładania konta;",
  "przypadkowy numer i Twoje głosy, żeby jeden głos liczył się jeden raz.",
];

const RIGHTS = [
  "zobaczyć swoje dane i dostać ich kopię;",
  "poprawić je;",
  "usunąć je albo ograniczyć ich użycie;",
  "wycofać zgodę w każdej chwili; to, co działo się wcześniej, pozostaje zgodne z prawem;",
  "złożyć skargę do Prezesa Urzędu Ochrony Danych Osobowych (uodo.gov.pl).",
];

function Section({
  children,
  title,
}: {
  children: React.ReactNode;
  title: string;
}) {
  return (
    <View style={styles.section}>
      <Heading level={2}>{title}</Heading>
      {children}
    </View>
  );
}

function Item({ children }: { children: React.ReactNode }) {
  return (
    <View role="listitem" style={styles.item}>
      <Txt aria-hidden>•</Txt>
      <Txt style={styles.grow}>{children}</Txt>
    </View>
  );
}

function List({ items }: { items: string[] }) {
  return (
    <View role="list" style={styles.list}>
      {items.map((item) => (
        <Item key={item}>{item}</Item>
      ))}
    </View>
  );
}

export default function PrivacyScreen() {
  return (
    <Screen
      back="Wyszukiwanie"
      backFallback="/"
      title="Jak chronimy Twoje dane"
      width={760}
    >
      <Head>
        <title>{`Jak chronimy Twoje dane · ${APP_NAME}`}</title>
        <meta
          content="Prostymi słowami: jakie dane zbiera HubMi, po co, kto je przetwarza i jak poprosić o ich usunięcie."
          name="description"
        />
      </Head>
      <Sheet raised>
        <Txt variant="lead">
          HubMi to prototyp przygotowany na hackathonie HackYeah 2026 dla
          Regionalnego Ośrodka Polityki Społecznej w Krakowie. Tu prostymi
          słowami piszemy, co dzieje się z danymi, które wpisujesz.
        </Txt>
        <Section title="Kto odpowiada za Twoje dane">
          <Txt>
            Gdy serwis zacznie działać na stałe, administratorem danych będzie
            Regionalny Ośrodek Polityki Społecznej w Krakowie, ul. Piastowska
            32, 30-070 Kraków. Dziś to prototyp: prowadzi go zespół, który go
            zbudował, a dane służą tylko do działania serwisu i odpowiedzi na
            Twoje sprawy.
          </Txt>
          <ExternalLink
            href={`${ROPS}/polityka-prywatnosci`}
            label="Polityka prywatności ROPS w Krakowie"
          />
        </Section>
        <Section title="Co zbieramy i po co">
          <Txt>
            Czytasz rozwiązania bez logowania i bez podawania danych. Dane
            zbieramy tylko wtedy, gdy sam lub sama wyślesz formularz:
          </Txt>
          <View role="list" style={styles.list}>
            {FORMS.map((form) => (
              <Item key={form.name}>
                <Txt weight="600">{`${form.name}: `}</Txt>
                {`${form.data}, ${form.why}.`}
              </Item>
            ))}
          </View>
          <Txt>
            Adres e-mail jest wszędzie nieobowiązkowy albo potrzebny tylko do
            kontaktu. W opisie nie wpisuj imion, adresów ani informacji o
            zdrowiu innych osób.
          </Txt>
        </Section>
        <Section title="Na jakiej podstawie">
          <Txt>
            Na podstawie Twojej zgody (art. 6 ust. 1 lit. a RODO). Zgodę dajesz,
            gdy zaznaczasz pole przy adresie e-mail i wysyłasz formularz.
          </Txt>
        </Section>
        <Section title="Kto pomaga nam przetwarzać dane">
          <List items={PROCESSORS} />
          <Txt>
            Google i Resend to firmy spoza Unii Europejskiej. Korzystamy z ich
            standardowych umów o ochronie danych.
          </Txt>
          <Txt>
            Dyktowanie głosem działa w Twojej przeglądarce lub telefonie.
            Nagranie przetwarza ich dostawca, na przykład Google albo Apple, nie
            my.
          </Txt>
        </Section>
        <Section title="Czego nie zapisujemy">
          <Txt>
            Nie zapisujemy tekstu, który wpisujesz w wyszukiwanie. Zostaje tylko
            anonimowa liczba wyszukiwań i to, jakie rozwiązania się pokazały.
            Nie używamy narzędzi analitycznych, reklam ani ciasteczek
            śledzących.
          </Txt>
        </Section>
        <Section title="Jak długo">
          <Txt>
            Dane trzymamy tak długo, jak trzeba, żeby zająć się Twoją sprawą,
            albo do wycofania zgody. Ten prototyp nie usuwa jeszcze starych
            danych sam. Usuniemy je na Twoją prośbę.
          </Txt>
        </Section>
        <Section title="Twoje prawa">
          <Txt>Masz prawo:</Txt>
          <List items={RIGHTS} />
          <Txt>
            Jak poprosić o usunięcie: w rozmowie o swoim zgłoszeniu, pomyśle lub
            wniosku (link dostajesz po wysłaniu formularza) możesz wycofać zgodę
            na kontakt. Możesz też napisać do ROPS w Krakowie.
          </Txt>
          <ExternalLink
            href={`${ROPS}/kontakt/regionalny-osrodek-polityki-spolecznej-w-krakowie`}
            label="Kontakt z ROPS w Krakowie"
          />
        </Section>
        <Section title="Co zostaje na Twoim urządzeniu">
          <Txt>
            Nie używamy ciasteczek do śledzenia ani do reklam, dlatego nie
            pytamy o zgodę na nie. W pamięci przeglądarki lub aplikacji
            zapisujemy tylko to, co jest potrzebne do działania serwisu:
          </Txt>
          <List items={DEVICE} />
          <Txt>
            Filmy z YouTube wczytujemy dopiero wtedy, gdy klikniesz, żeby je
            obejrzeć. Wszystko z tej listy usuniesz, czyszcząc dane strony w
            ustawieniach przeglądarki.
          </Txt>
        </Section>
      </Sheet>
    </Screen>
  );
}

const styles = StyleSheet.create({
  grow: {
    flex: 1,
  },
  item: {
    flexDirection: "row",
    gap: space.sm,
  },
  list: {
    gap: space.sm,
  },
  section: {
    gap: space.md,
    marginTop: space.lg,
  },
});
