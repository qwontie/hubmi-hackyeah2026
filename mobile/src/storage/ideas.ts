import AsyncStorage from "@react-native-async-storage/async-storage";
import { useEffect, useState } from "react";

const STORAGE_KEY = "hubmi.ideas.v1";

export interface StoredIdea {
  createdAt: string;
  id: string;
  number: number | null;
  title: string;
  token: string;
}

const listeners = new Set<(ideas: StoredIdea[]) => void>();

const read = async (): Promise<StoredIdea[]> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(parsed) ? (parsed as StoredIdea[]) : [];
  } catch {
    return [];
  }
};

const write = async (ideas: StoredIdea[]) => {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(ideas));
  for (const listener of listeners) {
    listener(ideas);
  }
};

export const saveIdea = async (idea: StoredIdea) => {
  const ideas = await read();
  await write([idea, ...ideas.filter((item) => item.id !== idea.id)]);
};

export const getIdea = async (id: string) =>
  (await read()).find((item) => item.id === id) ?? null;

export const updateIdea = async (id: string, patch: Partial<StoredIdea>) => {
  const ideas = await read();
  await write(
    ideas.map((item) => (item.id === id ? { ...item, ...patch } : item))
  );
};

export const listIdeas = read;

export const useStoredIdeas = () => {
  const [ideas, setIdeas] = useState<StoredIdea[] | null>(null);

  useEffect(() => {
    read()
      .then(setIdeas)
      .catch(() => setIdeas([]));
    listeners.add(setIdeas);
    return () => {
      listeners.delete(setIdeas);
    };
  }, []);

  return ideas;
};
