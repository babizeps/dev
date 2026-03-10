import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import type { Plant } from '../supabase/plants';
import { Colors } from '../constants/colors';

type Props = {
  plant: Plant;
  discovered: boolean;
  isPioneer: boolean;
  photoUrl?: string;
  onPress: () => void;
};

export default function PlantCard({ plant, discovered, isPioneer, photoUrl, onPress }: Props) {
  return (
    <TouchableOpacity
      style={[styles.card, discovered ? styles.cardDiscovered : styles.cardLocked, isPioneer && styles.cardPioneer]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      {discovered && photoUrl ? (
        <Image source={{ uri: photoUrl }} style={styles.photo} />
      ) : (
        <View style={[styles.photo, styles.photoPlaceholder]}>
          <Text style={styles.placeholderEmoji}>{discovered ? '🌿' : '❓'}</Text>
        </View>
      )}

      {isPioneer && <View style={styles.pioneerBadge}><Text style={styles.pioneerStar}>⭐</Text></View>}

      <View style={styles.info}>
        {discovered ? (
          <>
            <Text style={styles.scientific} numberOfLines={1}>{plant.scientific_name}</Text>
            {plant.common_name && (
              <Text style={styles.common} numberOfLines={1}>{plant.common_name}</Text>
            )}
          </>
        ) : (
          <>
            <Text style={styles.lockedName}>???</Text>
            <Text style={styles.lockedSub}>Not yet discovered</Text>
          </>
        )}
        <Text style={styles.count}>🔍 {plant.discovery_count}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 14,
    overflow: 'hidden',
    marginBottom: 12,
    borderWidth: 1,
  },
  cardDiscovered: {
    backgroundColor: Colors.card,
    borderColor: Colors.border,
  },
  cardLocked: {
    backgroundColor: Colors.cardLocked,
    borderColor: Colors.textDim,
    opacity: 0.65,
  },
  cardPioneer: {
    borderColor: Colors.pioneer,
    borderWidth: 2,
  },
  photo: {
    width: '100%',
    height: 130,
  },
  photoPlaceholder: {
    backgroundColor: Colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderEmoji: { fontSize: 40 },
  pioneerBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: Colors.pioneer,
    borderRadius: 12,
    padding: 4,
  },
  pioneerStar: { fontSize: 14 },
  info: { padding: 10 },
  scientific: { color: Colors.text, fontStyle: 'italic', fontWeight: '600', fontSize: 13 },
  common: { color: Colors.textMuted, fontSize: 12, marginTop: 2 },
  lockedName: { color: Colors.textDim, fontWeight: '700', fontSize: 14 },
  lockedSub: { color: Colors.textDim, fontSize: 11, marginTop: 2 },
  count: { color: Colors.textMuted, fontSize: 11, marginTop: 4 },
});
