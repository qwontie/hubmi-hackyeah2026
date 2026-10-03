import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const cladd = (...names: string[]) => names.map((n) => `cladd-${n}`);

const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      radius: cladd(
        "3xs",
        "2xs",
        "xs",
        "sm",
        "md",
        "lg",
        "xl",
        "2xl",
        "wrap-md",
        "panel",
        "popover",
        "dialog",
        "toast",
        "tooltip"
      ),
      shadow: cladd("outline", "outline-fill", "cut-outline", "popover"),
      spacing: cladd(
        "3xs",
        "2xs",
        "xs",
        "sm",
        "md",
        "lg",
        "xl",
        "2xl",
        "thumb-xs",
        "thumb-sm",
        "thumb-md",
        "nested-sm",
        "nested-md",
        "nested-lg"
      ),
      text: [
        ...cladd("md", "sm", "xs", "2xs", "3xs"),
        "hm-xs",
        "hm-sm",
        "hm-base",
        "hm-lg",
        "hm-xl",
        "hm-2xl",
        "hm-3xl",
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type WithoutChild<T> = T extends { child?: any } ? Omit<T, "child"> : T;
export type WithoutChildren<T> = T extends { children?: any }
  ? Omit<T, "children">
  : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & {
  ref?: U | null;
};
