"use client";

import { useQuery } from "@tanstack/react-query";
import { getLocations } from "@/lib/api";
import { PropertyFilters as Filters, PropertyType, ListingType, OrderBy, Location } from "@/lib/types";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid2";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import ListItemText from "@mui/material/ListItemText";
import Checkbox from "@mui/material/Checkbox";
import TextField from "@mui/material/TextField";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";

const TYPE_OPTIONS: { value: PropertyType; label: string }[] = [
  { value: "apartment", label: "Departamento" },
  { value: "house", label: "Casa" },
  { value: "ph", label: "PH" },
  { value: "land", label: "Terreno" },
  { value: "commercial", label: "Local" },
  { value: "office", label: "Oficina" },
  { value: "garage", label: "Cochera" },
  { value: "warehouse", label: "Galpón" },
];

interface FlatLocation {
  id: number;
  label: string;
  level: string;
}

function flattenLocations(locations: Location[], depth = 0): FlatLocation[] {
  const result: FlatLocation[] = [];
  const SKIP_LEVELS = new Set(["provincia", "departamento"]);
  for (const loc of locations) {
    if (!SKIP_LEVELS.has(loc.level)) {
      result.push({ id: loc.id, label: "\u00a0".repeat(depth * 2) + loc.name, level: loc.level });
    }
    if (loc.children?.length) {
      result.push(...flattenLocations(loc.children, SKIP_LEVELS.has(loc.level) ? depth : depth + 1));
    }
  }
  return result;
}

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export default function PropertyFilters({ filters, onChange }: Props) {
  const update = (partial: Partial<Filters>) => {
    onChange({ ...filters, ...partial, page: 1 });
  };

  const isSale = !filters.listing_type || filters.listing_type === "sale";

  const { data: locationTree } = useQuery({ queryKey: ["locations"], queryFn: getLocations, staleTime: Infinity });
  const flatLocations = locationTree ? flattenLocations(locationTree) : [];

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Grid container spacing={2} alignItems="center">

        <Grid size={{ xs: 6, md: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Ordenar por</InputLabel>
            <Select
              value={filters.order_by || "score_desc"}
              label="Ordenar por"
              onChange={(e) => update({ order_by: e.target.value as OrderBy })}
            >
              <MenuItem value="score_desc">Mejor precio</MenuItem>
              <MenuItem value="price_asc">Menor precio</MenuItem>
              <MenuItem value="price_desc">Mayor precio</MenuItem>
              <MenuItem value="newest">Más recientes</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid size={{ xs: 6, md: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Operacion</InputLabel>
            <Select
              value={filters.listing_type || ""}
              label="Operacion"
              onChange={(e) => {
                const val = (e.target.value || undefined) as ListingType | undefined;
                update({
                  listing_type: val,
                  // Reset apto_credito if switching away from sale
                  apto_credito: val && val !== "sale" ? undefined : filters.apto_credito,
                });
              }}
            >
              <MenuItem value="">Todas</MenuItem>
              <MenuItem value="sale">Venta</MenuItem>
              <MenuItem value="rent">Alquiler</MenuItem>
              <MenuItem value="temporary_rent">Temporal</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid size={{ xs: 6, md: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Tipo</InputLabel>
            <Select
              multiple
              value={filters.property_type || []}
              label="Tipo"
              onChange={(e) => {
                const val = e.target.value as PropertyType[];
                update({ property_type: val.length ? val : undefined });
              }}
              renderValue={(selected) =>
                (selected as PropertyType[]).map((v) => TYPE_OPTIONS.find((o) => o.value === v)?.label).join(", ")
              }
            >
              {TYPE_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value} dense>
                  <Checkbox checked={(filters.property_type || []).includes(opt.value)} size="small" />
                  <ListItemText primary={opt.label} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        <Grid size={{ xs: 6, md: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Dormitorios</InputLabel>
            <Select
              value={filters.bedrooms || ""}
              label="Dormitorios"
              onChange={(e) =>
                update({ bedrooms: e.target.value ? Number(e.target.value) : undefined })
              }
            >
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="1">1+</MenuItem>
              <MenuItem value="2">2+</MenuItem>
              <MenuItem value="3">3+</MenuItem>
              <MenuItem value="4">4+</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid size={{ xs: 6, md: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Zona</InputLabel>
            <Select
              value={filters.location_id || ""}
              label="Zona"
              onChange={(e) =>
                update({ location_id: e.target.value ? Number(e.target.value) : undefined })
              }
            >
              <MenuItem value="">Todas</MenuItem>
              {flatLocations.map((loc) => (
                <MenuItem key={loc.id} value={loc.id} sx={{ fontWeight: loc.level === "ciudad" ? 600 : 400 }}>
                  {loc.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        <Grid size={{ xs: 12, md: 3 }}>
          <Stack direction="row" spacing={1}>
            <TextField
              type="number"
              label="Precio min"
              size="small"
              fullWidth
              value={filters.min_price || ""}
              onChange={(e) =>
                update({ min_price: e.target.value ? Number(e.target.value) : undefined })
              }
            />
            <TextField
              type="number"
              label="Precio max"
              size="small"
              fullWidth
              value={filters.max_price || ""}
              onChange={(e) =>
                update({ max_price: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </Stack>
        </Grid>

        {isSale && (
          <Grid size={{ xs: 12, md: "auto" }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={!!filters.apto_credito}
                  onChange={(e) => update({ apto_credito: e.target.checked || undefined })}
                  size="small"
                  color="secondary"
                />
              }
              label="Apto crédito"
              sx={{ whiteSpace: "nowrap" }}
            />
          </Grid>
        )}

      </Grid>
    </Paper>
  );
}
