"use client";

import Link from "next/link";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardMedia from "@mui/material/CardMedia";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import FavoriteIcon from "@mui/icons-material/Favorite";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import { PropertyListItem } from "@/lib/types";
import { useFavorites } from "@/contexts/FavoritesContext";

const TYPE_LABELS: Record<string, string> = {
  apartment: "Departamento",
  house: "Casa",
  ph: "PH",
  land: "Terreno",
  commercial: "Local",
  office: "Oficina",
  garage: "Cochera",
  warehouse: "Galpon",
};

const LISTING_LABELS: Record<string, string> = {
  sale: "Venta",
  rent: "Alquiler",
  temporary_rent: "Alquiler Temporario",
};

const LISTING_COLORS: Record<string, "success" | "info" | "warning"> = {
  sale: "success",
  rent: "info",
  temporary_rent: "warning",
};

function formatPrice(property: PropertyListItem): string {
  if (property.current_price_usd && property.current_price_usd > 0) {
    return `USD ${Math.round(property.current_price_usd).toLocaleString("es-AR")}`;
  }
  if (property.current_price && property.current_price > 0) {
    return property.current_currency === "USD"
      ? `USD ${Math.round(property.current_price).toLocaleString("es-AR")}`
      : `$ ${Math.round(property.current_price).toLocaleString("es-AR")}`;
  }
  return "Consultar";
}

function ScoreBadge({ score, isOverall }: { score: number; isOverall?: boolean }) {
  const label = isOverall
    ? score >= 70 ? "Excelente" : score >= 40 ? "Bueno" : "Regular"
    : score >= 70 ? "Buen precio" : score >= 40 ? "Precio justo" : "Sobreprecio";
  const color = score >= 70 ? "success" : score >= 40 ? "warning" : "error";
  return <Chip label={label} color={color} size="small" />;
}

function ZoneBadge({ score }: { score: number }) {
  const color = score >= 60 ? "success" : score >= 40 ? "warning" : "error";
  const label = score >= 60 ? "Buena zona" : score >= 40 ? "Zona regular" : "Zona riesgosa";
  return <Chip label={label} color={color} size="small" variant="outlined" sx={{ fontSize: "0.65rem", height: 20 }} />;
}

export default function PropertyCard({ property }: { property: PropertyListItem }) {
  const { isFavorite, addFavorite, removeFavorite } = useFavorites();
  const fav = isFavorite(property.id);

  const handleFavClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (fav) removeFavorite(property.id);
    else addFavorite(property.id);
  };

  return (
    <Link href={`/properties/${property.id}`} style={{ display: "block", textDecoration: "none", color: "inherit" }}>
      <Card
        sx={{
          cursor: "pointer",
          display: "flex",
          position: "relative",
          "&:hover": {
            transform: "translateY(-2px)",
            boxShadow: 6,
          },
        }}
      >
        {/* Thumbnail */}
        {property.thumbnail_url ? (
          <CardMedia
            component="img"
            image={property.thumbnail_url}
            alt=""
            sx={{ width: 160, minHeight: 120, objectFit: "cover", flexShrink: 0 }}
          />
        ) : (
          <Box
            sx={{
              width: 160,
              minHeight: 120,
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "grey.200",
            }}
          >
            <HomeOutlinedIcon sx={{ fontSize: 40, color: "grey.400" }} />
          </Box>
        )}

        {/* Favorite button */}
        <IconButton
          onClick={handleFavClick}
          size="small"
          sx={{
            position: "absolute",
            top: 4,
            right: 4,
            bgcolor: "rgba(255,255,255,0.85)",
            "&:hover": { bgcolor: "rgba(255,255,255,1)" },
            zIndex: 1,
          }}
        >
          {fav ? <FavoriteIcon color="error" fontSize="small" /> : <FavoriteBorderIcon fontSize="small" />}
        </IconButton>

        {/* Content */}
        <CardContent sx={{ flex: 1, minWidth: 0, py: 1.5, "&:last-child": { pb: 1.5 } }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 0.5 }}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Typography variant="caption" color="text.secondary">
                {TYPE_LABELS[property.property_type] || property.property_type}
              </Typography>
              {property.overall_score != null ? (
                <ScoreBadge score={property.overall_score} isOverall />
              ) : property.price_score != null ? (
                <ScoreBadge score={property.price_score} />
              ) : null}
              {property.zone_score != null && <ZoneBadge score={property.zone_score} />}
            </Stack>
            <Chip
              label={LISTING_LABELS[property.listing_type] || property.listing_type}
              color={LISTING_COLORS[property.listing_type] || "default"}
              size="small"
              variant="outlined"
            />
          </Box>

          <Typography variant="h6" fontWeight="bold" gutterBottom sx={{ lineHeight: 1.3 }}>
            {formatPrice(property)}
          </Typography>

          {property.address && (
            <Typography variant="body2" color="text.secondary" noWrap sx={{ mb: 0.5 }}>
              {property.address}
            </Typography>
          )}

          <Stack direction="row" spacing={2} flexWrap="wrap">
            {property.total_area_m2 && (
              <Typography variant="caption" color="text.secondary">
                {property.total_area_m2} m²
              </Typography>
            )}
            {property.bedrooms && (
              <Typography variant="caption" color="text.secondary">
                {property.bedrooms} {property.bedrooms === 1 ? "dorm" : "dorms"}
              </Typography>
            )}
            {property.bathrooms && (
              <Typography variant="caption" color="text.secondary">
                {property.bathrooms} {property.bathrooms === 1 ? "baño" : "baños"}
              </Typography>
            )}
            {property.garages && (
              <Typography variant="caption" color="text.secondary">
                {property.garages} {property.garages === 1 ? "cochera" : "cocheras"}
              </Typography>
            )}
            {property.price_per_m2_usd && (
              <Typography variant="caption" color="secondary.main" fontWeight="bold">
                USD {property.price_per_m2_usd}/m²
              </Typography>
            )}
          </Stack>
        </CardContent>
      </Card>
    </Link>
  );
}
