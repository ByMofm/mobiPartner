"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { PriceContext } from "@/lib/types";

interface Props {
  context: PriceContext;
}

export default function PriceGauge({ context }: Props) {
  const theme = useTheme();
  const { price_usd, median_usd, min_usd, max_usd, comparables_count } = context;

  const range = max_usd - min_usd;
  if (range <= 0) return null;

  const pricePos = Math.max(0, Math.min(100, ((price_usd - min_usd) / range) * 100));
  const medianPos = Math.max(0, Math.min(100, ((median_usd - min_usd) / range) * 100));
  const isBelowMedian = price_usd <= median_usd;
  const priceColor = isBelowMedian ? theme.palette.success.main : theme.palette.error.main;

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
        Contexto de Precio ({comparables_count} similares)
      </Typography>

      {/* Bar */}
      <Box sx={{ position: "relative", height: 28, borderRadius: 2, overflow: "visible", mb: 3, mt: 2 }}>
        {/* Background gradient bar */}
        <Box
          sx={{
            position: "absolute",
            top: 8,
            left: 0,
            right: 0,
            height: 12,
            borderRadius: 1,
            background: `linear-gradient(90deg, ${theme.palette.success.light} 0%, ${theme.palette.warning.light} 50%, ${theme.palette.error.light} 100%)`,
          }}
        />

        {/* Median marker */}
        <Box
          sx={{
            position: "absolute",
            top: 4,
            left: `${medianPos}%`,
            transform: "translateX(-50%)",
            width: 2,
            height: 20,
            bgcolor: theme.palette.text.primary,
            borderRadius: 1,
          }}
        />

        {/* Price marker */}
        <Box
          sx={{
            position: "absolute",
            top: 2,
            left: `${pricePos}%`,
            transform: "translateX(-50%)",
            width: 16,
            height: 24,
            borderRadius: "50%",
            bgcolor: priceColor,
            border: `3px solid ${theme.palette.background.paper}`,
            boxShadow: 2,
          }}
        />
      </Box>

      {/* Labels */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Box>
          <Typography variant="caption" color="text.secondary" display="block">
            Min
          </Typography>
          <Typography variant="caption" fontWeight="bold">
            USD {min_usd.toLocaleString("es-AR")}
          </Typography>
        </Box>
        <Box sx={{ textAlign: "center" }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Mediana
          </Typography>
          <Typography variant="caption" fontWeight="bold">
            USD {median_usd.toLocaleString("es-AR")}
          </Typography>
        </Box>
        <Box sx={{ textAlign: "center" }}>
          <Typography variant="caption" display="block" sx={{ color: priceColor, fontWeight: "bold" }}>
            Esta propiedad
          </Typography>
          <Typography variant="caption" fontWeight="bold" sx={{ color: priceColor }}>
            USD {price_usd.toLocaleString("es-AR")}
          </Typography>
        </Box>
        <Box sx={{ textAlign: "right" }}>
          <Typography variant="caption" color="text.secondary" display="block">
            Max
          </Typography>
          <Typography variant="caption" fontWeight="bold">
            USD {max_usd.toLocaleString("es-AR")}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
