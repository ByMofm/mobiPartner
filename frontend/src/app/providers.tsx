"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import ThemeRegistry from "@/components/ThemeRegistry";
import { FavoritesProvider } from "@/contexts/FavoritesContext";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeRegistry>
        <FavoritesProvider>{children}</FavoritesProvider>
      </ThemeRegistry>
    </QueryClientProvider>
  );
}
