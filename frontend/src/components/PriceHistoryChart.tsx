"use client";

import { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { PriceHistory } from "@/lib/types";

interface Props {
  priceHistory: PriceHistory[];
  medianUsd?: number;
}

export default function PriceHistoryChart({ priceHistory, medianUsd }: Props) {
  const theme = useTheme();

  const data = useMemo(() => {
    return priceHistory
      .filter((ph) => ph.price_usd != null)
      .sort((a, b) => new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime())
      .map((ph) => ({
        date: new Date(ph.scraped_at).toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" }),
        price_usd: ph.price_usd,
      }));
  }, [priceHistory]);

  if (data.length <= 1) return null;

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
        Evolucion de Precio (USD)
      </Typography>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value: number) => [`USD ${value.toLocaleString("es-AR")}`, "Precio"]}
            contentStyle={{
              background: theme.palette.background.paper,
              border: `1px solid ${theme.palette.divider}`,
              borderRadius: 8,
            }}
          />
          {medianUsd && (
            <ReferenceLine
              y={medianUsd}
              stroke={theme.palette.text.disabled}
              strokeDasharray="5 5"
              label={{
                value: `Mediana: USD ${medianUsd.toLocaleString("es-AR")}`,
                position: "insideTopRight",
                fontSize: 11,
                fill: theme.palette.text.secondary,
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="price_usd"
            stroke={theme.palette.secondary.main}
            strokeWidth={2}
            dot={{ r: 4, fill: theme.palette.secondary.main }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
}
