import { Platform } from "react-native";

export const APP_NAME = "HubMi";
export const ORGANIZATION_NAME = "Małopolski Hub Innowacji Społecznych";

export const API_BASE =
  Platform.OS === "web"
    ? ""
    : (process.env.EXPO_PUBLIC_API_URL ?? "https://hubmi.qwontie.dev");

export const TEXT_MIN = 10;
export const TEXT_MAX = 2000;
