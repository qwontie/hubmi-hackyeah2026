import { Platform } from "react-native";

export const nightAttr = (night: boolean): Record<string, unknown> =>
  night && Platform.OS === "web" ? { dataSet: { night: "true" } } : {};
