"use client";

import { useQuery } from "@tanstack/react-query";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Link from "next/link";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import PropertyCard from "@/components/PropertyCard";
import { useFavorites } from "@/contexts/FavoritesContext";
import { getPropertiesByIds } from "@/lib/api";

export default function FavoritesPage() {
  const { favorites } = useFavorites();

  const { data, isLoading } = useQuery({
    queryKey: ["favorites", favorites],
    queryFn: () => getPropertiesByIds(favorites),
    enabled: favorites.length > 0,
  });

  if (favorites.length === 0) {
    return (
      <Container maxWidth="md" sx={{ py: 8, textAlign: "center" }}>
        <FavoriteBorderIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          No tenes propiedades guardadas
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Marca propiedades con el corazon para verlas aca.
        </Typography>
        <Button component={Link} href="/properties" variant="contained" color="secondary">
          Explorar propiedades
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight="bold" sx={{ mb: 3 }}>
        Favoritos ({favorites.length})
      </Typography>

      {isLoading ? (
        <Stack spacing={2}>
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} variant="rectangular" height={120} sx={{ borderRadius: 2 }} animation="wave" />
          ))}
        </Stack>
      ) : (
        <Stack spacing={2}>
          {data?.items.map((property) => (
            <PropertyCard key={property.id} property={property} />
          ))}
        </Stack>
      )}
    </Container>
  );
}
