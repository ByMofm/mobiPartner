"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { getMapProperties } from "@/lib/api";
import { PropertyMapItem, PropertyFilters } from "@/lib/types";

interface Bbox {
  minLat: number;
  minLng: number;
  maxLat: number;
  maxLng: number;
}

export function useMap(filters: PropertyFilters = {}) {
  const [bbox, setBbox] = useState<Bbox | null>(null);

  const params: Record<string, string | string[]> = {};
  if (filters.property_type?.length) params.property_type = filters.property_type;
  if (filters.listing_type) params.listing_type = filters.listing_type;
  if (bbox) {
    params.bbox = `${bbox.minLat},${bbox.minLng},${bbox.maxLat},${bbox.maxLng}`;
  }

  const { data: markers = [], isLoading } = useQuery<PropertyMapItem[]>({
    queryKey: ["map-properties", params],
    queryFn: () => getMapProperties(params),
    enabled: bbox !== null,
  });

  const updateBbox = useCallback((newBbox: Bbox) => {
    setBbox(newBbox);
  }, []);

  return { markers, isLoading, updateBbox };
}
