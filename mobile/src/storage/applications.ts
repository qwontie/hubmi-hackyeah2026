import AsyncStorage from "@react-native-async-storage/async-storage";
import { useEffect, useState } from "react";
import type { ApplicationStatus } from "@/api/types";

const STORAGE_KEY = "hubmi.applications.v1";

export interface StoredApplication {
  callId: string;
  callTitle: string;
  createdAt: string;
  id: string;
  ideaId: string | null;
  ideaTitle: string | null;
  status: ApplicationStatus;
  submittedAt: string | null;
  token: string;
}

const listeners = new Set<(applications: StoredApplication[]) => void>();

const read = async (): Promise<StoredApplication[]> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(parsed) ? (parsed as StoredApplication[]) : [];
  } catch {
    return [];
  }
};

const write = async (applications: StoredApplication[]) => {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(applications));
  for (const listener of listeners) {
    listener(applications);
  }
};

let queue: Promise<void> = Promise.resolve();

const mutate = (
  change: (applications: StoredApplication[]) => StoredApplication[] | null
) => {
  const next = queue
    .catch(() => undefined)
    .then(async () => {
      const changed = change(await read());
      if (changed) {
        await write(changed);
      }
    });
  queue = next;
  return next;
};

export const saveApplication = (application: StoredApplication) =>
  mutate((applications) => [
    application,
    ...applications.filter((item) => item.id !== application.id),
  ]);

export const updateApplication = (
  id: string,
  patch: Partial<StoredApplication>
) =>
  mutate((applications) => {
    const current = applications.find((item) => item.id === id);
    if (
      !current ||
      Object.entries(patch).every(
        ([key, value]) => current[key as keyof StoredApplication] === value
      )
    ) {
      return null;
    }
    return applications.map((item) =>
      item.id === id ? { ...item, ...patch } : item
    );
  });

export const forgetApplication = (id: string) =>
  mutate((applications) => applications.filter((item) => item.id !== id));

export const getApplication = async (id: string) =>
  (await read()).find((item) => item.id === id) ?? null;

export const listApplications = read;

export const useStoredApplications = () => {
  const [applications, setApplications] = useState<StoredApplication[] | null>(
    null
  );

  useEffect(() => {
    read()
      .then(setApplications)
      .catch(() => setApplications([]));
    listeners.add(setApplications);
    return () => {
      listeners.delete(setApplications);
    };
  }, []);

  return applications;
};
