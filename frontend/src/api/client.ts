import axios from "axios";
import { PersonEvent, VehicleEvent, MediaAsset } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const client = axios.create({
  baseURL: API_BASE_URL,
});

export const apiBaseUrl = API_BASE_URL;

export function getMediaUrl(asset?: MediaAsset | null): string | null {
  if (!asset) return null;
  const base = API_BASE_URL.replace(/\/+$/, "");
  return `${base}/media/${asset.id}`;
}

export async function fetchRecentVehicles(limit = 10): Promise<VehicleEvent[]> {
  const res = await client.get<VehicleEvent[]>(`/vehicles/recent?limit=${limit}`);
  return res.data;
}

export async function fetchRecentPersons(limit = 10): Promise<PersonEvent[]> {
  const res = await client.get<PersonEvent[]>(`/persons/recent?limit=${limit}`);
  return res.data;
}

export async function filterEvents(params: { camera?: string; event_type?: string; start?: string; end?: string; limit?: number }): Promise<{
  person_events: PersonEvent[];
  vehicle_events: VehicleEvent[];
}> {
  const res = await client.post("/events/filter", params);
  return res.data;
}
