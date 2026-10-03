export interface SelectOption {
  label: string;
  value: string;
}

export const isAbort = (error: unknown) =>
  error instanceof Error && error.name === "AbortError";
