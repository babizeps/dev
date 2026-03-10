import { supabase } from './client';

export type Discovery = {
  id: string;
  user_id: string;
  plant_id: string;
  photo_url: string | null;
  location_lat: number | null;
  location_lng: number | null;
  ai_confidence: number | null;
  is_pioneer: boolean;
  discovered_at: string;
  plants?: {
    scientific_name: string;
    common_name: string | null;
  };
};

export async function getUserDiscoveries(userId: string): Promise<Discovery[]> {
  const { data, error } = await supabase
    .from('discoveries')
    .select('*, plants(scientific_name, common_name)')
    .eq('user_id', userId)
    .order('discovered_at', { ascending: false });
  if (error) throw error;
  return data ?? [];
}

export async function getUserDiscoveredPlantIds(userId: string): Promise<Set<string>> {
  const { data, error } = await supabase
    .from('discoveries')
    .select('plant_id')
    .eq('user_id', userId);
  if (error) throw error;
  return new Set((data ?? []).map((d) => d.plant_id));
}
