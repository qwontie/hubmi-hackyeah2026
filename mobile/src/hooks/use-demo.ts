import { useEffect, useState } from "react";
import { api } from "@/api/client";

let known: boolean | null = null;
let pending: Promise<boolean> | null = null;

const load = () => {
  pending ??= api
    .meta()
    .then((meta) => meta.demo === true)
    .catch(() => {
      pending = null;
      return false;
    });
  return pending;
};

export const DEMO_WORDS = "dane pokazowe";

export const useDemo = () => {
  const [demo, setDemo] = useState(known ?? false);

  useEffect(() => {
    let live = true;
    load().then((value) => {
      known = value;
      if (live) {
        setDemo(value);
      }
    });
    return () => {
      live = false;
    };
  }, []);

  return demo;
};
