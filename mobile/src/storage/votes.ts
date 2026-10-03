import AsyncStorage from "@react-native-async-storage/async-storage";

const VOTER_KEY = "hubmi.voter.v1";
const VOTES_KEY = "hubmi.votes.v1";
const ALPHABET =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

export type MyVote = "up" | "down";

let voterCache: string | null = null;

const randomBytes = (length: number) => {
  const bytes = new Uint8Array(length);
  if (typeof globalThis.crypto?.getRandomValues === "function") {
    globalThis.crypto.getRandomValues(bytes);
    return bytes;
  }
  for (let i = 0; i < length; i += 1) {
    bytes[i] = Math.floor(Math.random() * 256);
  }
  return bytes;
};

const randomId = () =>
  Array.from(randomBytes(32), (byte) => ALPHABET[byte % ALPHABET.length]).join(
    ""
  );

export const voterId = async () => {
  if (voterCache) {
    return voterCache;
  }
  const stored = await AsyncStorage.getItem(VOTER_KEY).catch(() => null);
  if (stored) {
    voterCache = stored;
    return stored;
  }
  const fresh = randomId();
  voterCache = fresh;
  await AsyncStorage.setItem(VOTER_KEY, fresh).catch(() => undefined);
  return fresh;
};

const readVotes = async (): Promise<Record<string, MyVote>> => {
  try {
    const raw = await AsyncStorage.getItem(VOTES_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : {};
    return parsed && typeof parsed === "object"
      ? (parsed as Record<string, MyVote>)
      : {};
  } catch {
    return {};
  }
};

export const getMyVote = async (slug: string) =>
  (await readVotes())[slug] ?? null;

export const setMyVote = async (slug: string, vote: MyVote | null) => {
  const votes = await readVotes();
  if (vote) {
    votes[slug] = vote;
  } else {
    delete votes[slug];
  }
  await AsyncStorage.setItem(VOTES_KEY, JSON.stringify(votes));
};
