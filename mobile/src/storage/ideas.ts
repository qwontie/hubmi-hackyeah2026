import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "hubmi.ideas.v1";

export interface StoredIdea {
  createdAt: string;
  id: string;
  number: number;
  title: string;
  token: string;
}

export const saveIdea = async (idea: StoredIdea) => {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  const parsed = raw ? (JSON.parse(raw) as unknown) : [];
  const ideas = Array.isArray(parsed) ? (parsed as StoredIdea[]) : [];
  await AsyncStorage.setItem(
    STORAGE_KEY,
    JSON.stringify([idea, ...ideas.filter((item) => item.id !== idea.id)])
  );
};
