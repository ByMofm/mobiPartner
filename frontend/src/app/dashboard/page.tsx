"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getStatsOverview, getScheduleStatus, triggerScrape, triggerGeocode, triggerScore, triggerDedup, triggerAssignLocations, triggerBackfillAptoCredito, triggerPipeline } from "@/lib/api";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import CircularProgress from "@mui/material/CircularProgress";

const SOURCE_LABELS: Record<string, string> = {
  zonaprop: "ZonaProp",
  argenprop: "Argenprop",
  mercadolibre: "MercadoLibre",
};

type JobState = "idle" | "running" | "done" | "error";
type JobResult = { message: string; color: "success" | "error" | "info" };

function useJob(fn: () => Promise<unknown>) {
  const [state, setState] = useState<JobState>("idle");
  const [result, setResult] = useState<JobResult | null>(null);

  const run = async () => {
    setState("running");
    setResult(null);
    try {
      const data = await fn() as Record<string, unknown>;
      setState("done");
      if (data.pid) {
        setResult({ message: `Iniciado (PID ${data.pid})`, color: "info" });
      } else if (data.status === "started" && data.pending !== undefined) {
        setResult({ message: `Geocodificando ${data.pending} propiedades en background`, color: "info" });
      } else if (data.status === "nothing_to_do") {
        setResult({ message: "Todas las propiedades ya tienen coordenadas", color: "success" });
      } else {
        setResult({ message: "Completado", color: "success" });
      }
    } catch (e: unknown) {
      setState("error");
      setResult({ message: e instanceof Error ? e.message : "Error desconocido", color: "error" });
    }
  };

  return { state, result, run };
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStatsOverview,
  });
  const { data: schedule, refetch: refetchSchedule } = useQuery({
    queryKey: ["schedule"],
    queryFn: getScheduleStatus,
    refetchInterval: 10000, // poll every 10s while pipeline is running
  });

  const zonaprop = useJob(() => triggerScrape("zonaprop"));
  const argenprop = useJob(() => triggerScrape("argenprop"));
  const mercadolibre = useJob(() => triggerScrape("mercadolibre"));
  const geocode = useJob(() => triggerGeocode());
  const score = useJob(triggerScore);
  const dedup = useJob(triggerDedup);
  const assignLocs = useJob(triggerAssignLocations);
  const backfillApto = useJob(triggerBackfillAptoCredito);
  const pipeline = useJob(triggerPipeline);

  const refreshStats = () => queryClient.invalidateQueries({ queryKey: ["stats"] });

  if (isLoading && !stats) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h5" fontWeight="bold" sx={{ mb: 3 }}>
          Dashboard
        </Typography>
        <Grid container spacing={2}>
          {[1, 2, 3, 4].map((i) => (
            <Grid key={i} size={{ xs: 12, sm: 6, lg: 3 }}>
              <Skeleton variant="rectangular" height={100} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight="bold" sx={{ mb: 3 }}>
        Dashboard
      </Typography>

      {stats && (
        <Grid container spacing={2} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Total Propiedades
              </Typography>
              <Typography variant="h4" fontWeight="bold">
                {stats.total_properties.toLocaleString("es-AR")}
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Activas
              </Typography>
              <Typography variant="h4" fontWeight="bold" color="success.main">
                {stats.active_properties.toLocaleString("es-AR")}
              </Typography>
              {stats.without_coords > 0 && (
                <Typography variant="caption" color="warning.main">
                  {stats.without_coords.toLocaleString("es-AR")} sin coordenadas
                </Typography>
              )}
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Precio Promedio Venta (USD)
              </Typography>
              <Typography variant="h5" fontWeight="bold">
                {stats.avg_price_usd_sale
                  ? `USD ${Math.round(stats.avg_price_usd_sale).toLocaleString("es-AR")}`
                  : "Sin datos"}
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Precio Promedio Alquiler (USD)
              </Typography>
              <Typography variant="h5" fontWeight="bold">
                {stats.avg_price_usd_rent
                  ? `USD ${Math.round(stats.avg_price_usd_rent).toLocaleString("es-AR")}`
                  : "Sin datos"}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {stats && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Publicaciones por Fuente
          </Typography>
          <Table size="small">
            <TableBody>
              {Object.entries(stats.sources).map(([source, count]) => (
                <TableRow key={source}>
                  <TableCell>{SOURCE_LABELS[source] || source}</TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="bold">{(count as number).toLocaleString("es-AR")}</Typography>
                  </TableCell>
                </TableRow>
              ))}
              <TableRow>
                <TableCell>
                  <Typography fontWeight="bold">Total</Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography fontWeight="bold">{stats.total_listings.toLocaleString("es-AR")}</Typography>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Paper>
      )}

      {schedule && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }}>
            <Typography variant="h6">Pipeline automático</Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              {schedule.last_run_status === "running" && <CircularProgress size={16} />}
              {schedule.last_run_status && (
                <Chip
                  label={schedule.last_run_status === "completed" ? "Completado" : schedule.last_run_status === "error" ? "Error" : "Corriendo"}
                  color={schedule.last_run_status === "completed" ? "success" : schedule.last_run_status === "error" ? "error" : "info"}
                  size="small"
                />
              )}
              <Button
                variant="contained"
                color="secondary"
                size="small"
                onClick={async () => { await pipeline.run(); refetchSchedule(); }}
                disabled={pipeline.state === "running" || schedule.last_run_status === "running"}
                startIcon={pipeline.state === "running" ? <CircularProgress size={14} color="inherit" /> : undefined}
              >
                Correr ahora
              </Button>
            </Stack>
          </Stack>
          <Stack direction="row" spacing={3}>
            <Box>
              <Typography variant="caption" color="text.secondary">Horario</Typography>
              <Typography variant="body2" fontWeight={600}>{schedule.schedule} (20:00 ARG)</Typography>
            </Box>
            {schedule.next_run_at && (
              <Box>
                <Typography variant="caption" color="text.secondary">Próxima ejecución</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {new Date(schedule.next_run_at).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" })}
                </Typography>
              </Box>
            )}
            {schedule.last_run_at && (
              <Box>
                <Typography variant="caption" color="text.secondary">Última ejecución</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {new Date(schedule.last_run_at).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" })}
                </Typography>
              </Box>
            )}
          </Stack>
          {schedule.last_run_steps.length > 0 && (
            <Table size="small" sx={{ mt: 2 }}>
              <TableBody>
                {schedule.last_run_steps.map((step) => (
                  <TableRow key={step.step}>
                    <TableCell sx={{ py: 0.5 }}>{step.step}</TableCell>
                    <TableCell sx={{ py: 0.5 }}>
                      <Chip
                        label={step.status === "ok" ? "OK" : "Error"}
                        color={step.status === "ok" ? "success" : "error"}
                        size="small"
                      />
                    </TableCell>
                    <TableCell sx={{ py: 0.5 }} align="right">
                      <Typography variant="caption" color="text.secondary">{step.elapsed_s}s</Typography>
                    </TableCell>
                    <TableCell sx={{ py: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        {step.error || (step.result ? JSON.stringify(step.result) : "")}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      )}

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 0.5 }}>
          Acciones manuales
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Disparar scrapers y procesos de mantenimiento individualmente
        </Typography>

        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
          Scrapers
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          {([
            { key: "zonaprop", label: "ZonaProp", job: zonaprop },
            { key: "argenprop", label: "Argenprop", job: argenprop },
            { key: "mercadolibre", label: "MercadoLibre", job: mercadolibre },
          ] as const).map(({ label, job }) => (
            <Stack key={label} direction="row" spacing={1} alignItems="center">
              <Button
                variant="outlined"
                size="small"
                onClick={job.run}
                disabled={job.state === "running"}
                startIcon={job.state === "running" ? <CircularProgress size={14} /> : undefined}
              >
                {label}
              </Button>
              {job.result && (
                <Chip label={job.result.message} color={job.result.color} size="small" />
              )}
            </Stack>
          ))}
        </Stack>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
          Mantenimiento
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {([
            {
              label: stats?.without_coords
                ? `Geocodificar faltantes (${stats.without_coords.toLocaleString("es-AR")})`
                : "Geocodificar faltantes",
              job: geocode,
              help: "Asigna coordenadas via Nominatim a todas las propiedades sin ubicación",
            },
            { label: "Calcular Scores", job: score, help: "Recalcula score de precio USD" },
            { label: "Deduplicar", job: dedup, help: "Detecta y fusiona duplicados" },
            { label: "Asignar Zonas", job: assignLocs, help: "Asigna location_id a propiedades por texto de dirección" },
            { label: "Backfill Apto Crédito", job: backfillApto, help: "Detecta apto crédito en URLs y datos existentes" },
          ] as const).map(({ label, job, help }) => (
            <Stack key={label} direction="row" spacing={1} alignItems="center">
              <Button
                variant="outlined"
                color="secondary"
                size="small"
                onClick={async () => { await job.run(); refreshStats(); }}
                disabled={job.state === "running"}
                startIcon={job.state === "running" ? <CircularProgress size={14} color="inherit" /> : undefined}
                title={help}
              >
                {label}
              </Button>
              {job.result && (
                <Chip label={job.result.message} color={job.result.color} size="small" />
              )}
            </Stack>
          ))}
        </Stack>
      </Paper>
    </Container>
  );
}
