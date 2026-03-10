import { create } from 'zustand';

export type Achievement = {
  key: string;
  name: string;
  description: string;
  unlockedAt: string | null;
};

type GameState = {
  totalXp: number;
  level: number;
  pioneerCount: number;
  discoveredPlantIds: Set<string>;
  pendingXpGain: number | null; // triggers XP popup animation
  pendingAchievement: Achievement | null; // triggers badge animation
  setProfile: (xp: number, level: number, pioneerCount: number) => void;
  setDiscoveredPlantIds: (ids: Set<string>) => void;
  addDiscovery: (plantId: string, xpGained: number, isPioneer: boolean) => void;
  clearPendingXp: () => void;
  clearPendingAchievement: () => void;
  setPendingAchievement: (achievement: Achievement) => void;
};

export const LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 2000, 4000, 8000];
export const LEVEL_TITLES = [
  'Seedling', 'Sprout', 'Sapling', 'Tree',
  'Forest Guardian', 'Rainforest Elder', 'Ancient One', 'Legend',
];

export function xpToLevel(xp: number): number {
  let level = 1;
  for (let i = 1; i < LEVEL_THRESHOLDS.length; i++) {
    if (xp >= LEVEL_THRESHOLDS[i]) level = i + 1;
    else break;
  }
  return level;
}

export const useGameStore = create<GameState>((set) => ({
  totalXp: 0,
  level: 1,
  pioneerCount: 0,
  discoveredPlantIds: new Set(),
  pendingXpGain: null,
  pendingAchievement: null,

  setProfile: (xp, level, pioneerCount) => set({ totalXp: xp, level, pioneerCount }),

  setDiscoveredPlantIds: (ids) => set({ discoveredPlantIds: ids }),

  addDiscovery: (plantId, xpGained, isPioneer) =>
    set((state) => {
      const newIds = new Set(state.discoveredPlantIds);
      newIds.add(plantId);
      const newXp = state.totalXp + xpGained;
      return {
        discoveredPlantIds: newIds,
        totalXp: newXp,
        level: xpToLevel(newXp),
        pioneerCount: isPioneer ? state.pioneerCount + 1 : state.pioneerCount,
        pendingXpGain: xpGained,
      };
    }),

  clearPendingXp: () => set({ pendingXpGain: null }),
  clearPendingAchievement: () => set({ pendingAchievement: null }),
  setPendingAchievement: (achievement) => set({ pendingAchievement: achievement }),
}));
