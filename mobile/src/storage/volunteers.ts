import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "hubmi.volunteer-tokens";

const read = async (): Promise<Record<string, string>> => {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : {};
  } catch {
    return {};
  }
};

export const getVolunteerToken = async (id: string) =>
  (await read())[id] ?? null;

export const saveVolunteerToken = async (id: string, token: string) => {
  const tokens = await read();
  await AsyncStorage.setItem(KEY, JSON.stringify({ ...tokens, [id]: token }));
};
