"use client";

import { createContext, useMemo, useState, useEffect, ReactNode, useRef } from "react";
import { ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import createCache, { type EmotionCache } from "@emotion/cache";
import { CacheProvider, useServerInsertedHTML } from "@emotion/react";
import { lightTheme, darkTheme } from "@/lib/theme";

export const ColorModeContext = createContext({
  toggleColorMode: () => {},
  mode: "light" as "light" | "dark",
});

function useEmotionCache(): EmotionCache {
  const [emotionCache] = useState(() => {
    const cache = createCache({ key: "mui", prepend: true });
    cache.compat = true;
    return cache;
  });
  return emotionCache;
}

export default function ThemeRegistry({ children }: { children: ReactNode }) {
  const emotionCache = useEmotionCache();
  const [mode, setMode] = useState<"light" | "dark">("light");

  useEffect(() => {
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (stored === "dark" || (!stored && prefersDark)) {
      setMode("dark");
    }
  }, []);

  const colorMode = useMemo(
    () => ({
      toggleColorMode: () => {
        setMode((prev) => {
          const next = prev === "light" ? "dark" : "light";
          localStorage.setItem("theme", next);
          return next;
        });
      },
      mode,
    }),
    [mode]
  );

  const theme = mode === "dark" ? darkTheme : lightTheme;

  return (
    <CacheProvider value={emotionCache}>
      <ColorModeContext.Provider value={colorMode}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </ColorModeContext.Provider>
    </CacheProvider>
  );
}
