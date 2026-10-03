import AsyncStorage from "@react-native-async-storage/async-storage";
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "hubmi.needs.v1";

export interface StoredNeed {
  clusterTitle: string | null;
  contactEmail: string | null;
  createdAt: string;
  id: string;
  nothingFits: boolean;
  number: number | null;
  text: string;
  token: string;
}

const listeners = new Set<(needs: StoredNeed[]) => void>();

const read = async (): Promise<StoredNeed[]> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(parsed) ? (parsed as StoredNeed[]) : [];
  } catch {
    return [];
  }
};

const write = async (needs: StoredNeed[]) => {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(needs));
  for (const listener of listeners) {
    listener(needs);
  }
};

export const saveNeed = async (need: StoredNeed) => {
  const needs = await read();
  await write([need, ...needs.filter((item) => item.id !== need.id)]);
};

export const updateNeed = async (id: string, patch: Partial<StoredNeed>) => {
  const needs = await read();
  await write(
    needs.map((item) => (item.id === id ? { ...item, ...patch } : item))
  );
};

export const forgetNeed = async (id: string) => {
  const needs = await read();
  await write(needs.filter((item) => item.id !== id));
};

export const useStoredNeeds = () => {
  const [needs, setNeeds] = useState<StoredNeed[] | null>(null);

  const refresh = useCallback(() => {
    read()
      .then(setNeeds)
      .catch(() => setNeeds([]));
  }, []);

  useEffect(() => {
    refresh();
    listeners.add(setNeeds);
    return () => {
      listeners.delete(setNeeds);
    };
  }, [refresh]);

  return needs;
};

export const getNeed = async (id: string) =>
  (await read()).find((item) => item.id === id) ?? null;
