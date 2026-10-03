import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  AccessibilityInfo,
  Platform,
  useColorScheme,
  useWindowDimensions,
} from "react-native";
import {
  baseType,
  type Palette,
  palettes,
  type TextScaleKey,
  type TypeRole,
  textScales,
  wideBreakpoint,
} from "./tokens";

const STORAGE_KEY = "hubmi.settings.v1";

export interface Settings {
  highContrast: boolean;
  reduceMotion: boolean;
  textScale: TextScaleKey;
}

const defaults: Settings = {
  highContrast: false,
  reduceMotion: false,
  textScale: "standard",
};

interface Theme {
  borderWidth: number;
  colors: Palette;
  dark: boolean;
  highContrast: boolean;
  lineHeight: (size: number) => number;
  reduceMotion: boolean;
  reduceTransparency: boolean;
  type: Record<TypeRole, number>;
  wide: boolean;
}

const REDUCED_TRANSPARENCY = "(prefers-reduced-transparency: reduce)";

const webReducedTransparency = () =>
  Platform.OS === "web" &&
  typeof window !== "undefined" &&
  window.matchMedia?.(REDUCED_TRANSPARENCY).matches === true;

const pickPalette = (highContrast: boolean, dark: boolean) => {
  if (highContrast) {
    return palettes.contrast;
  }
  return dark ? palettes.dark : palettes.standard;
};

interface SettingsContextValue {
  settings: Settings;
  theme: Theme;
  update: (patch: Partial<Settings>) => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

const isTextScale = (value: unknown): value is TextScaleKey =>
  textScales.some((scale) => scale.key === value);

const parse = (raw: string | null): Settings => {
  if (!raw) {
    return defaults;
  }
  try {
    const value = JSON.parse(raw) as Partial<Settings>;
    return {
      highContrast: value.highContrast === true,
      reduceMotion: value.reduceMotion === true,
      textScale: isTextScale(value.textScale)
        ? value.textScale
        : defaults.textScale,
    };
  } catch {
    return defaults;
  }
};

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(defaults);
  const [systemReduceMotion, setSystemReduceMotion] = useState(false);
  const [reduceTransparency, setReduceTransparency] = useState(
    webReducedTransparency
  );
  const { width } = useWindowDimensions();
  const dark = useColorScheme() === "dark";

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => setSettings(parse(raw)))
      .catch(() => setSettings(defaults));
  }, []);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled()
      .then(setSystemReduceMotion)
      .catch(() => setSystemReduceMotion(false));
    const subscription = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      setSystemReduceMotion
    );
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    if (Platform.OS !== "ios") {
      return;
    }
    AccessibilityInfo.isReduceTransparencyEnabled()
      .then(setReduceTransparency)
      .catch(() => setReduceTransparency(false));
    const subscription = AccessibilityInfo.addEventListener(
      "reduceTransparencyChanged",
      setReduceTransparency
    );
    return () => subscription.remove();
  }, []);

  const update = useCallback((patch: Partial<Settings>) => {
    setSettings((current) => {
      const next = { ...current, ...patch };
      AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(
        () => undefined
      );
      return next;
    });
  }, []);

  const theme = useMemo<Theme>(() => {
    const factor =
      textScales.find((scale) => scale.key === settings.textScale)?.factor ?? 1;
    const wide = width >= wideBreakpoint;
    const type = Object.fromEntries(
      Object.entries(baseType).map(([role, size]) => {
        const narrowed =
          !wide && (role === "h1" || role === "display") ? size * 0.86 : size;
        return [role, Math.round(narrowed * factor)];
      })
    ) as Record<TypeRole, number>;
    return {
      borderWidth: settings.highContrast ? 2 : 1,
      colors: pickPalette(settings.highContrast, dark),
      dark: dark && !settings.highContrast,
      highContrast: settings.highContrast,
      lineHeight: (size: number) => Math.round(size * 1.45),
      reduceMotion: settings.reduceMotion || systemReduceMotion,
      reduceTransparency: reduceTransparency || settings.highContrast,
      type,
      wide,
    };
  }, [settings, systemReduceMotion, reduceTransparency, dark, width]);

  const value = useMemo(
    () => ({ settings, theme, update }),
    [settings, update, theme]
  );

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => {
  const value = useContext(SettingsContext);
  if (!value) {
    throw new Error("useSettings outside SettingsProvider");
  }
  return value;
};

export const useTheme = () => useSettings().theme;
