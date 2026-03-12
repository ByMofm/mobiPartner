"use client";

import { useEffect, useRef, useCallback } from "react";
import { PropertyMapItem, PropertyFilters } from "@/lib/types";
import { useMap } from "@/hooks/useMap";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

const TUCUMAN_CENTER: [number, number] = [-26.8083, -65.2176];
const DEFAULT_ZOOM = 13;

const MARKER_COLORS: Record<string, string> = {
  sale: "#22c55e",
  rent: "#3b82f6",
  temporary_rent: "#f97316",
};

const TYPE_LABELS: Record<string, string> = {
  apartment: "Depto",
  house: "Casa",
  ph: "PH",
  land: "Terreno",
  commercial: "Local",
  office: "Oficina",
  garage: "Cochera",
  warehouse: "Galpon",
};

interface Props {
  filters: PropertyFilters;
  onMarkerClick?: (id: number) => void;
}

function formatPopupPrice(prop: PropertyMapItem): string {
  if (prop.current_price_usd && prop.current_price_usd > 0) {
    return `USD ${Math.round(prop.current_price_usd).toLocaleString("es-AR")}`;
  }
  if (prop.current_price) {
    return `${prop.current_currency || ""} ${prop.current_price.toLocaleString("es-AR")}`;
  }
  return "Consultar";
}

export default function PropertyMap({ filters, onMarkerClick }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<any>(null);
  const markerGroupRef = useRef<any>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { markers, isLoading, updateBbox } = useMap(filters);
  const updateBboxRef = useRef(updateBbox);
  useEffect(() => { updateBboxRef.current = updateBbox; }, [updateBbox]);

  useEffect(() => {
    if (!mapRef.current || leafletMapRef.current) return;

    const container = mapRef.current as any;
    if (container._leaflet_id) return;

    const initMap = async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");
      await import("leaflet.markercluster");
      await import("leaflet.markercluster/dist/MarkerCluster.css");
      await import("leaflet.markercluster/dist/MarkerCluster.Default.css");

      if (!mapRef.current || leafletMapRef.current) return;

      const map = L.map(mapRef.current, {
        center: TUCUMAN_CENTER,
        zoom: DEFAULT_ZOOM,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      // @ts-ignore
      const clusterGroup = L.markerClusterGroup({
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
      });
      map.addLayer(clusterGroup);

      leafletMapRef.current = map;
      markerGroupRef.current = clusterGroup;

      const bounds = map.getBounds();
      updateBboxRef.current({
        minLat: bounds.getSouth(),
        minLng: bounds.getWest(),
        maxLat: bounds.getNorth(),
        maxLng: bounds.getEast(),
      });

      map.on("moveend", () => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
          const b = map.getBounds();
          updateBboxRef.current({
            minLat: b.getSouth(),
            minLng: b.getWest(),
            maxLat: b.getNorth(),
            maxLng: b.getEast(),
          });
        }, 300);
      });
    };

    initMap();

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
        markerGroupRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!markerGroupRef.current || !leafletMapRef.current) return;

    const updateMarkers = async () => {
      const L = (await import("leaflet")).default;
      const group = markerGroupRef.current;
      group.clearLayers();

      markers.forEach((prop: PropertyMapItem) => {
        if (prop.latitude == null || prop.longitude == null) return;

        const color = MARKER_COLORS[prop.listing_type] || "#6b7280";

        const icon = L.divIcon({
          className: "custom-marker",
          html: `<div style="
            width: 16px; height: 16px;
            background: ${color};
            border: 2px solid white;
            border-radius: 50%;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3);
          "></div>`,
          iconSize: [16, 16],
          iconAnchor: [8, 8],
        });

        const marker = L.marker([prop.latitude, prop.longitude], { icon });

        const priceStr = formatPopupPrice(prop);
        const typeLabel = TYPE_LABELS[prop.property_type] || prop.property_type;
        const thumbHtml = prop.thumbnail_url
          ? `<img src="${prop.thumbnail_url}" style="width:100%;height:80px;object-fit:cover;border-radius:4px;margin-bottom:6px;" />`
          : "";
        const addressHtml = prop.address
          ? `<div style="font-size:11px;color:#666;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;">${prop.address}</div>`
          : "";
        const specsHtml = [
          prop.total_area_m2 ? `${prop.total_area_m2} m²` : "",
          prop.bedrooms ? `${prop.bedrooms} dorm` : "",
        ]
          .filter(Boolean)
          .join(" · ");

        marker.bindPopup(
          `<div style="min-width:180px;max-width:220px;font-family:Inter,sans-serif;">
            ${thumbHtml}
            <div style="font-weight:700;font-size:14px;margin-bottom:2px;">${priceStr}</div>
            ${addressHtml}
            <div style="font-size:12px;color:#888;margin-bottom:6px;">${typeLabel}${specsHtml ? " · " + specsHtml : ""}</div>
            <a href="/properties/${prop.id}" style="font-size:12px;color:#3483FA;text-decoration:none;font-weight:500;">Ver detalle &rarr;</a>
          </div>`,
          { maxWidth: 240 }
        );

        group.addLayer(marker);
      });
    };

    updateMarkers();
  }, [markers, onMarkerClick]);

  return (
    <Box sx={{ position: "relative" }}>
      <Box ref={mapRef} sx={{ width: "100%", height: 500, borderRadius: 2, border: 1, borderColor: "divider" }} />
      {isLoading && (
        <Chip
          label="Cargando..."
          size="small"
          sx={{ position: "absolute", top: 8, right: 8, bgcolor: "background.paper" }}
        />
      )}
      <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Box sx={{ width: 12, height: 12, borderRadius: "50%", bgcolor: "#22c55e" }} />
          <Typography variant="caption" color="text.secondary">Venta</Typography>
        </Stack>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Box sx={{ width: 12, height: 12, borderRadius: "50%", bgcolor: "#3b82f6" }} />
          <Typography variant="caption" color="text.secondary">Alquiler</Typography>
        </Stack>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Box sx={{ width: 12, height: 12, borderRadius: "50%", bgcolor: "#f97316" }} />
          <Typography variant="caption" color="text.secondary">Temporal</Typography>
        </Stack>
      </Stack>
    </Box>
  );
}
