import { View, Text, StyleSheet, TouchableOpacity, Image, Platform } from 'react-native';
import type { Plant } from '../supabase/plants';
import { Colors } from '../constants/colors';
import { PixelPlant } from './PixelPlant';

const mono = Platform.OS === 'ios' ? 'Courier New' : 'monospace';

type Props = {
  plant: Plant;
  discovered: boolean;
  isPioneer: boolean;
  photoUrl?: string;
  onPress: () => void;
  entryIndex: number;
  selected?: boolean;
};

export default function PlantCard({ plant, discovered, isPioneer, photoUrl, onPress, entryIndex, selected }: Props) {
  const numStr = String(entryIndex).padStart(3, '0');

  return (
    <TouchableOpacity
      style={[
        styles.cell,
        (isPioneer || selected) && styles.cellSelected,
        !discovered && styles.cellLocked,
      ]}
      onPress={onPress}
      activeOpacity={0.75}
    >
      {/* Caught indicator dot (top-left) */}
      {discovered && (
        <View style={styles.caughtDot} />
      )}

      {/* Entry number (top-right) */}
      <Text style={styles.number}>{numStr}</Text>

      {/* Plant image or placeholder */}
      <View style={styles.imageArea}>
        {discovered && photoUrl ? (
          <Image
            source={{ uri: photoUrl }}
            style={[styles.image, !discovered && styles.imageLocked]}
          />
        ) : (
          <PixelPlant seed={entryIndex} locked={!discovered} size={5} />
        )}
        {!discovered && <View style={styles.lockedOverlay} />}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  cell: {
    aspectRatio: 1,
    backgroundColor: Colors.contentBg,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderTopColor: Colors.pixelHighlight,
    borderLeftColor: Colors.pixelHighlight,
    borderBottomColor: Colors.pixelShadow,
    borderRightColor: Colors.pixelShadow,
    overflow: 'hidden',
    position: 'relative',
    flex: 1,
  },
  cellSelected: {
    borderTopColor: Colors.infoBoxBorder,
    borderLeftColor: Colors.infoBoxBorder,
    borderBottomColor: '#8B0000',
    borderRightColor: '#8B0000',
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
  },
  cellLocked: {
    backgroundColor: '#D8D8D8',
  },
  caughtDot: {
    position: 'absolute',
    top: 4,
    left: 4,
    width: 6,
    height: 6,
    borderRadius: 0,
    backgroundColor: Colors.infoBoxBorder,
    zIndex: 2,
  },
  number: {
    position: 'absolute',
    top: 3,
    right: 4,
    fontSize: 9,
    fontFamily: mono,
    color: Colors.darkTextMuted,
    zIndex: 2,
  },
  imageArea: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  image: {
    width: '80%',
    height: '80%',
    resizeMode: 'cover',
  },
  imageLocked: {
    opacity: 0.15,
  },
  lockedOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#000000',
    opacity: 0.35,
  },
});
