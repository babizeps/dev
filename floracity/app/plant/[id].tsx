import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Image, SafeAreaView, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getPlantById, type Plant } from '../../src/supabase/plants';
import { supabase } from '../../src/supabase/client';
import { useGameStore } from '../../src/store/gameStore';
import { Colors } from '../../src/constants/colors';

type CommunityPhoto = { photo_url: string; profiles: unknown };

export default function PlantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { discoveredPlantIds } = useGameStore();
  const [plant, setPlant] = useState<Plant | null>(null);
  const [communityPhotos, setCommunityPhotos] = useState<CommunityPhoto[]>([]);
  const [firstDiscoverer, setFirstDiscoverer] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getPlantById(id).then(setPlant);

    supabase
      .from('discoveries')
      .select('photo_url, profiles(username)')
      .eq('plant_id', id)
      .not('photo_url', 'is', null)
      .limit(9)
      .then(({ data }) => setCommunityPhotos((data ?? []) as CommunityPhoto[]));
  }, [id]);

  useEffect(() => {
    if (!plant?.first_discovered_by) return;
    supabase
      .from('profiles')
      .select('username')
      .eq('id', plant.first_discovered_by)
      .single()
      .then(({ data }) => setFirstDiscoverer(data?.username ?? null));
  }, [plant?.first_discovered_by]);

  if (!plant) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.loading}>Loading...</Text>
      </SafeAreaView>
    );
  }

  const isDiscovered = discoveredPlantIds.has(plant.id);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>

        {/* Hero photo */}
        {communityPhotos[0] ? (
          <Image source={{ uri: communityPhotos[0].photo_url }} style={styles.hero} />
        ) : (
          <View style={[styles.hero, styles.heroPlaceholder]}>
            <Text style={styles.heroEmoji}>{isDiscovered ? '🌿' : '❓'}</Text>
          </View>
        )}

        {/* Pioneer badge */}
        {firstDiscoverer && (
          <View style={styles.pioneerBanner}>
            <Text style={styles.pioneerText}>⭐ First discovered by @{firstDiscoverer}</Text>
          </View>
        )}

        <Text style={styles.scientific}>{plant.scientific_name}</Text>
        {plant.common_name && <Text style={styles.common}>{plant.common_name}</Text>}
        {plant.malay_name && <Text style={styles.malay}>{plant.malay_name}</Text>}

        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statNum}>{plant.discovery_count}</Text>
            <Text style={styles.statLabel}>Discoveries</Text>
          </View>
          {plant.family && (
            <View style={styles.stat}>
              <Text style={styles.statNum}>{plant.family}</Text>
              <Text style={styles.statLabel}>Family</Text>
            </View>
          )}
        </View>

        {plant.description && (
          <>
            <Text style={styles.sectionTitle}>About</Text>
            <Text style={styles.description}>{plant.description}</Text>
          </>
        )}

        {plant.wikipedia_url && (
          <Text style={styles.wikiLink}>🔗 Wikipedia</Text>
        )}

        {/* Community photos */}
        {communityPhotos.length > 1 && (
          <>
            <Text style={styles.sectionTitle}>Community Photos</Text>
            <View style={styles.photoGrid}>
              {communityPhotos.slice(1).map((p, i) => (
                <Image key={i} source={{ uri: p.photo_url }} style={styles.gridPhoto} />
              ))}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  loading: { color: Colors.textMuted, textAlign: 'center', marginTop: 40 },
  content: { padding: 0, paddingBottom: 40 },
  backBtn: { padding: 16 },
  backText: { color: Colors.primary, fontSize: 16 },
  hero: { width: '100%', height: 280 },
  heroPlaceholder: { backgroundColor: Colors.surface, justifyContent: 'center', alignItems: 'center' },
  heroEmoji: { fontSize: 80 },
  pioneerBanner: {
    backgroundColor: Colors.accent + '22',
    borderBottomWidth: 1,
    borderColor: Colors.accent + '44',
    padding: 10,
    alignItems: 'center',
  },
  pioneerText: { color: Colors.accent, fontWeight: '700', fontSize: 13 },
  scientific: {
    color: Colors.text, fontSize: 26, fontWeight: '800',
    fontStyle: 'italic', padding: 16, paddingBottom: 4,
  },
  common: { color: Colors.primaryLight, fontSize: 17, paddingHorizontal: 16, paddingBottom: 4 },
  malay: { color: Colors.textMuted, fontSize: 14, paddingHorizontal: 16, paddingBottom: 12 },
  statsRow: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 14,
    gap: 24,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  stat: { alignItems: 'center' },
  statNum: { color: Colors.text, fontWeight: '800', fontSize: 18 },
  statLabel: { color: Colors.textMuted, fontSize: 11, marginTop: 2 },
  sectionTitle: { color: Colors.text, fontSize: 17, fontWeight: '700', paddingHorizontal: 16, marginBottom: 8 },
  description: { color: Colors.textMuted, paddingHorizontal: 16, lineHeight: 22, fontSize: 15, marginBottom: 16 },
  wikiLink: { color: Colors.primary, paddingHorizontal: 16, marginBottom: 16 },
  photoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    gap: 6,
  },
  gridPhoto: { width: '31%', aspectRatio: 1, borderRadius: 8 },
});
