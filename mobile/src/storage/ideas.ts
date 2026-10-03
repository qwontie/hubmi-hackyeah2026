import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "hubmi.ideas.v1";

export interface StoredIdea {
  createdAt: string;
  id: string;
  number: number | null;
  title: string;
  token: string;
}

const read = async (): Promise<StoredIdea[]> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(parsed) ? (parsed as StoredIdea[]) : [];
  } catch {
    return [];
  }
};

export const saveIdea = async (idea: StoredIdea) => {
  const ideas = await read();
  await AsyncStorage.setItem(
    STORAGE_KEY,
    JSON.stringify([idea, ...ideas.filter((item) => item.id !== idea.id)])
  );
};

export const getIdea = async (id: string) =>
  (await read()).find((item) => item.id === id) ?? null;

export const updateIdea = async (id: string, patch: Partial<StoredIdea>) => {
  const ideas = await read();
  await AsyncStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(
      ideas.map((item) => (item.id === id ? { ...item, ...patch } : item))
    )
  );
};

export const listIdeas = read;
