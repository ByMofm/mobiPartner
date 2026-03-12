"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid2";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Skeleton from "@mui/material/Skeleton";
import Fade from "@mui/material/Fade";
import ApartmentIcon from "@mui/icons-material/Apartment";
import SourceIcon from "@mui/icons-material/Source";
import UpdateIcon from "@mui/icons-material/Update";
import SearchIcon from "@mui/icons-material/Search";
import { getStatsOverview, getProperties } from "@/lib/api";
import PropertyCard from "@/components/PropertyCard";
import type { ListingType, PropertyType } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [operation, setOperation] = useState<ListingType | "">("");
  const [propertyType, setPropertyType] = useState<PropertyType | "">("");

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: getStatsOverview,
  });

  const { data: featured } = useQuery({
    queryKey: ["featured-properties"],
    queryFn: () => getProperties({ order_by: "score_desc", page_size: 4 }),
  });

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (operation) params.set("listing_type", operation);
    if (propertyType) params.set("property_type", propertyType);
    router.push(`/properties?${params.toString()}`);
  };

  return (
    <Box>
      {/* Hero */}
      <Box
        sx={{
          py: { xs: 6, md: 10 },
          textAlign: "center",
          background: (theme) =>
            theme.palette.mode === "dark"
              ? "linear-gradient(135deg, #1A1A2E 0%, #16213E 100%)"
              : "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
        }}
      >
        <Container maxWidth="md">
          <Typography variant="h3" fontWeight="bold" gutterBottom>
            Encontra tu proxima propiedad en Tucuman
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 4, maxWidth: 600, mx: "auto" }}>
            Datos de ZonaProp, Argenprop y MercadoLibre en un solo lugar. Precios analizados y comparados.
          </Typography>

          {/* Search Bar */}
          <Paper
            sx={{
              p: 2,
              maxWidth: 700,
              mx: "auto",
              display: "flex",
              gap: 2,
              flexWrap: { xs: "wrap", md: "nowrap" },
              alignItems: "center",
            }}
          >
            <FormControl size="small" sx={{ minWidth: 140, flex: 1 }}>
              <InputLabel>Operacion</InputLabel>
              <Select
                value={operation}
                label="Operacion"
                onChange={(e) => setOperation(e.target.value as ListingType | "")}
              >
                <MenuItem value="">Todas</MenuItem>
                <MenuItem value="sale">Venta</MenuItem>
                <MenuItem value="rent">Alquiler</MenuItem>
                <MenuItem value="temporary_rent">Temporario</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 140, flex: 1 }}>
              <InputLabel>Tipo</InputLabel>
              <Select
                value={propertyType}
                label="Tipo"
                onChange={(e) => setPropertyType(e.target.value as PropertyType | "")}
              >
                <MenuItem value="">Todos</MenuItem>
                <MenuItem value="apartment">Departamento</MenuItem>
                <MenuItem value="house">Casa</MenuItem>
                <MenuItem value="ph">PH</MenuItem>
                <MenuItem value="land">Terreno</MenuItem>
                <MenuItem value="commercial">Local</MenuItem>
              </Select>
            </FormControl>
            <Button
              variant="contained"
              color="secondary"
              startIcon={<SearchIcon />}
              onClick={handleSearch}
              sx={{ minWidth: 120, height: 40 }}
            >
              Buscar
            </Button>
          </Paper>
        </Container>
      </Box>

      {/* Stats */}
      <Container maxWidth="md" sx={{ py: 6 }}>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Paper sx={{ p: 3, textAlign: "center" }}>
              <ApartmentIcon color="secondary" sx={{ fontSize: 36, mb: 1 }} />
              <Typography variant="h4" fontWeight="bold">
                {stats ? stats.active_properties.toLocaleString("es-AR") : <Skeleton width={80} sx={{ mx: "auto" }} />}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Propiedades activas
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Paper sx={{ p: 3, textAlign: "center" }}>
              <SourceIcon color="secondary" sx={{ fontSize: 36, mb: 1 }} />
              <Typography variant="h4" fontWeight="bold">
                3
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Fuentes de datos
              </Typography>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Paper sx={{ p: 3, textAlign: "center" }}>
              <UpdateIcon color="secondary" sx={{ fontSize: 36, mb: 1 }} />
              <Typography variant="h4" fontWeight="bold">
                Diaria
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Actualizacion
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Container>

      {/* Featured Properties */}
      <Box sx={{ bgcolor: "background.default", py: 6 }}>
        <Container maxWidth="md">
          <Typography variant="h5" fontWeight="bold" sx={{ mb: 3 }}>
            Propiedades destacadas
          </Typography>
          {featured ? (
            <Fade in timeout={400}>
              <Stack spacing={2}>
                {featured.items.map((property) => (
                  <PropertyCard key={property.id} property={property} />
                ))}
              </Stack>
            </Fade>
          ) : (
            <Stack spacing={2}>
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} variant="rectangular" height={120} sx={{ borderRadius: 2 }} animation="wave" />
              ))}
            </Stack>
          )}
          <Box sx={{ textAlign: "center", mt: 4 }}>
            <Button
              component={Link}
              href="/properties"
              variant="contained"
              color="secondary"
              size="large"
            >
              Explorar todas las propiedades
            </Button>
          </Box>
        </Container>
      </Box>
    </Box>
  );
}
