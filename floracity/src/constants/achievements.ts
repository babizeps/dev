export type AchievementDef = {
  key: string;
  name: string;
  description: string;
  icon: string;
};

export const ACHIEVEMENTS: AchievementDef[] = [
  { key: 'first_bloom', name: 'First Bloom', description: 'Discover your first plant', icon: '🌱' },
  { key: 'pioneer', name: 'Pioneer', description: 'Be the first to discover a species', icon: '🏆' },
  { key: 'collector_10', name: 'Collector', description: 'Discover 10 different species', icon: '📚' },
  { key: 'collector_25', name: 'Botanist', description: 'Discover 25 different species', icon: '🔬' },
  { key: 'daily_explorer', name: 'Daily Explorer', description: 'Discover a plant 5 days in a row', icon: '🗓️' },
  { key: 'national_pride', name: 'National Pride', description: 'Discover Hibiscus rosa-sinensis', icon: '🌺' },
  { key: 'mangrove_walker', name: 'Mangrove Walker', description: 'Discover 5 mangrove species', icon: '🌊' },
  { key: 'cartographer', name: 'Cartographer', description: 'Log a plant at 3 different locations', icon: '🗺️' },
];
