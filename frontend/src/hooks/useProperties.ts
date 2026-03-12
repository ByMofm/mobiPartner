"use client";

import { useQuery } from "@tanstack/react-query";
import { getProperties, getProperty } from "@/lib/api";
import { PropertyFilters } from "@/lib/types";

export function useProperties(filters: PropertyFilters = {}) {
  return useQuery({
    queryKey: ["properties", filters],
    queryFn: () => getProperties(filters),
  });
}

export function useProperty(id: number) {
  return useQuery({
    queryKey: ["property", id],
    queryFn: () => getProperty(id),
    enabled: !!id,
  });
}
