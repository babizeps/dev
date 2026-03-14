import React from 'react';
import { View, StyleSheet } from 'react-native';

// Color palette
const C: Record<number, string> = {
  0: 'transparent',
  1: '#4CAF50', // green
  2: '#2E7D32', // dark green
  3: '#FFD700', // yellow
  4: '#FF8F00', // orange
  5: '#E91E63', // pink
  6: '#9C27B0', // purple
  7: '#795548', // brown
  8: '#FF5722', // red-orange
  9: '#81C784', // light green
};

// Locked color palette (grayscale)
const LOCKED: Record<number, string> = {
  0: 'transparent',
  1: '#888', 2: '#555', 3: '#999', 4: '#777',
  5: '#888', 6: '#666', 7: '#555', 8: '#777', 9: '#aaa',
};

// Pixel art sprites — each is a 2D array of color indices
const SPRITES: number[][][] = [
  // 0 — Sunflower
  [
    [0,0,0,3,3,3,0,0],
    [0,0,3,4,4,3,3,0],
    [0,3,3,4,4,3,3,0],
    [0,0,3,4,4,3,3,0],
    [0,0,0,3,3,3,0,0],
    [0,0,0,1,0,0,0,0],
    [0,0,1,1,1,0,0,0],
    [0,1,2,0,0,0,0,0],
  ],
  // 1 — Rose
  [
    [0,0,5,5,5,0,0,0],
    [0,5,5,8,5,5,0,0],
    [5,5,8,8,8,5,5,0],
    [0,5,5,8,5,5,0,0],
    [0,0,5,5,5,0,0,0],
    [0,0,0,1,0,0,0,0],
    [0,0,1,1,0,0,0,0],
    [0,1,2,0,0,0,0,0],
  ],
  // 2 — Tree/Bush
  [
    [0,0,1,1,1,0,0,0],
    [0,1,2,1,2,1,0,0],
    [1,1,1,2,1,1,1,0],
    [0,1,2,1,1,1,0,0],
    [0,0,1,1,2,0,0,0],
    [0,0,0,7,0,0,0,0],
    [0,0,0,7,0,0,0,0],
    [0,0,7,7,7,0,0,0],
  ],
  // 3 — Cactus
  [
    [0,0,0,1,0,0,0,0],
    [0,0,0,1,0,0,0,0],
    [0,1,0,1,0,1,0,0],
    [0,1,1,1,1,1,0,0],
    [0,0,1,1,1,0,0,0],
    [0,0,0,1,0,0,0,0],
    [0,0,7,7,7,0,0,0],
    [0,7,7,7,7,7,0,0],
  ],
  // 4 — Tulip
  [
    [0,0,0,6,0,0,0,0],
    [0,0,6,6,6,0,0,0],
    [0,6,6,6,6,6,0,0],
    [0,5,6,6,6,5,0,0],
    [0,0,5,5,5,0,0,0],
    [0,0,0,1,0,0,0,0],
    [0,0,1,1,0,0,0,0],
    [0,1,2,0,0,0,0,0],
  ],
  // 5 — Fern
  [
    [1,0,0,0,0,1,0,0],
    [0,1,0,0,1,0,0,0],
    [2,1,0,2,1,0,0,0],
    [0,2,1,1,2,0,0,0],
    [0,0,2,2,0,0,0,0],
    [0,0,0,2,0,0,0,0],
    [0,0,7,7,0,0,0,0],
    [0,7,7,7,7,0,0,0],
  ],
  // 6 — Mushroom
  [
    [0,0,8,8,8,0,0,0],
    [0,8,8,8,8,8,0,0],
    [8,8,4,8,4,8,8,0],
    [8,8,8,8,8,8,8,0],
    [0,9,9,9,9,9,0,0],
    [0,0,9,9,9,0,0,0],
    [0,0,7,7,7,0,0,0],
    [0,0,0,0,0,0,0,0],
  ],
  // 7 — Bamboo
  [
    [0,1,1,0,1,1,0,0],
    [0,1,2,1,1,2,0,0],
    [0,2,1,2,2,1,0,0],
    [0,1,2,1,1,2,0,0],
    [0,2,1,2,2,1,0,0],
    [0,1,2,0,1,2,0,0],
    [0,2,0,0,0,2,0,0],
    [0,7,7,0,7,7,0,0],
  ],
];

type Props = {
  seed: number;
  size?: number; // pixel size in dp (default 5)
  locked?: boolean;
};

export function PixelPlant({ seed, size = 5, locked = false }: Props) {
  const sprite = SPRITES[seed % SPRITES.length];
  const palette = locked ? LOCKED : C;

  return (
    <View style={styles.container}>
      {sprite.map((row, rowIdx) => (
        <View key={rowIdx} style={styles.row}>
          {row.map((colorIdx, colIdx) => (
            <View
              key={colIdx}
              style={{
                width: size,
                height: size,
                backgroundColor: palette[colorIdx] ?? 'transparent',
              }}
            />
          ))}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
  row: { flexDirection: 'row' },
});
