import { supabase } from './client';
import { MOCK_LEADERBOARD } from '../mock/data';

const MOCK_MODE = process.env.EXPO_PUBLIC_MOCK_MODE === 'true';

export type LeaderboardEntry = {
  id: string;
  username: string | null;
  avatar_url: string | null;
  total_xp: number;
  level: number;
  pioneer_count: number;
  species_count: number;
};

export async function getLeaderboard(limit = 50): Promise<LeaderboardEntry[]> {
  if (MOCK_MODE) return MOCK_LEADERBOARD.slice(0, limit);
  const { data, error } = await supabase
    .from('leaderboard')
    .select('*')
    .limit(limit);
  if (error) throw error;
  return data ?? [];
}

export function subscribeToLeaderboard(callback: (entries: LeaderboardEntry[]) => void) {
  if (MOCK_MODE) return () => {};
  const channel = supabase
    .channel('leaderboard-changes')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'profiles' }, async () => {
      const entries = await getLeaderboard();
      callback(entries);
    })
    .subscribe();
  return () => supabase.removeChannel(channel);
}
