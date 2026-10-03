import { ApiError } from "@/api/client";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export const isEmail = (value: string) => EMAIL.test(value);

export const EMAIL_INVALID =
  "Ten adres e-mail jest niepełny. Wzór: jan@poczta.pl.";

export const fieldMessage = (error: unknown, field: string) =>
  error instanceof ApiError
    ? (error.fields.find((item) => item.field === field)?.message ?? null)
    : null;
