import { supabase } from './client';
import { MOCK_PLANTS } from '../mock/data';

const MOCK_MODE = process.env.EXPO_PUBLIC_MOCK_MODE === 'true';

export type Plant = {
  id: string;
  scientific_name: string;
  common_name: string | null;
  malay_name: string | null;
  family: string | null;
  description: string | null;
  habitat: string | null;
  wikipedia_url: string | null;
  first_discovered_by: string | null;
  first_discovered_at: string | null;
  discovery_count: number;
  created_at: string;
};

export async function getAllPlants(): Promise<Plant[]> {
  if (MOCK_MODE) return [...MOCK_PLANTS].sort((a, b) => b.discovery_count - a.discovery_count);
  const { data, error } = await supabase
    .from('plants')
    .select('*')
    .order('discovery_count', { ascending: false });
  if (error) throw error;
  return data ?? [];
}

export async function getPlantById(id: string): Promise<Plant | null> {
  if (MOCK_MODE) return MOCK_PLANTS.find((p) => p.id === id) ?? null;
  const { data, error } = await supabase
    .from('plants')
    .select('*')
    .eq('id', id)
    .single();
  if (error) return null;
  return data;
}
