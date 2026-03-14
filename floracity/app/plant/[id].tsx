import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Image, TouchableOpacity, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getPlantById, type Plant } from '../../src/supabase/plants';
import { supabase } from '../../src/supabase/client';
import { useGameStore } from '../../src/store/gameStore';
import { Colors } from '../../src/constants/colors';

type CommunityPhoto = { photo_url: string; profiles: unknown };

const mono = Platform.OS === 'ios' ? 'Courier New' : 'monospace';

function StarRating({ count }: { count: number }) {
  const stars = Math.min(5, Math.max(1, Math.ceil(count / 10)));
  return (
    <Text style={styles.stars}>
      {'★'.repeat(stars)}{'☆'.repeat(5 - stars)}
    </Text>
  );
}

export default function PlantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { discoveredPlantIds } = useGameStore();
  const [plant, setPlant] = useState<Plant | null>(null);
  const [communityPhotos, setCommunityPhotos] = useState<CommunityPhoto[]>([]);
  const [firstDiscoverer, setFirstDiscoverer] = useState<string | null>(null);
  const [entryIndex, setEntryIndex] = useState<number | null>(null);

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

    // Get approximate entry index from plants table order
    supabase
      .from('plants')
      .select('id')
      .order('created_at', { ascending: true })
      .then(({ data }) => {
        if (data) {
          const idx = data.findIndex(p => p.id === id);
          if (idx >= 0) setEntryIndex(idx + 1);
        }
      });
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
      <View style={styles.container}>
        <View style={styles.infoHeader}>
          <Text style={styles.infoHeaderTitle}>▼ INFO</Text>
        </View>
        <View style={styles.loadingArea}>
          <Text style={styles.loading}>Loading...</Text>
        </View>
      </View>
    );
  }

  const isDiscovered = discoveredPlantIds.has(plant.id);
  const numStr = entryIndex ? String(entryIndex).padStart(3, '0') : '???';
  const displayName = (plant.common_name ?? plant.scientific_name).toUpperCase();

  return (
    <View style={styles.container}>
      {/* ▼ INFO header bar */}
      <View style={styles.infoHeader}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.infoHeaderTitle}>◀ INFO</Text>
        </TouchableOpacity>
        <View style={styles.flBadge}><Text style={styles.flBadgeText}>FL</Text></View>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {/* Top panel: image + info box */}
        <View style={styles.topPanel}>
          {/* Plant image */}
          <View style={styles.imageBox}>
            {communityPhotos[0] ? (
              <Image source={{ uri: communityPhotos[0].photo_url }} style={styles.plantImage} />
            ) : (
              <View style={styles.imagePlaceholder}>
                <Text style={styles.placeholderEmoji}>{isDiscovered ? '🌿' : '❓'}</Text>
              </View>
            )}
          </View>

          {/* Info box (right side) */}
          <View style={styles.infoBox}>
            {/* Number + Name */}
            <View style={styles.infoRow}>
              <Text style={styles.infoNumName} numberOfLines={2}>
                {numStr}{'\n'}{displayName}
              </Text>
            </View>
            <View style={styles.infoDivider} />

            {/* Star rating */}
            <View style={styles.infoRow}>
              <StarRating count={plant.discovery_count} />
            </View>
            <View style={styles.infoDivider} />

            {/* Stats */}
            <View style={styles.infoRow}>
              <Text style={styles.statLine}>
                <Text style={styles.statKey}>DISC </Text>
                <Text style={styles.statVal}>{plant.discovery_count}</Text>
              </Text>
            </View>
            {plant.family && (
              <>
                <View style={styles.infoDivider} />
                <View style={styles.infoRow}>
                  <Text style={styles.statLine} numberOfLines={2}>
                    <Text style={styles.statKey}>FAM  </Text>
                    <Text style={styles.statVal}>{plant.family.toUpperCase()}</Text>
                  </Text>
                </View>
              </>
            )}
          </View>
        </View>

        {/* Pioneer banner */}
        {firstDiscoverer && (
          <View style={styles.pioneerBanner}>
            <Text style={styles.pioneerText}>⭐ First discovered by @{firstDiscoverer}</Text>
          </View>
        )}

        {/* Scientific / Malay names */}
        <View style={styles.namesBox}>
          <Text style={styles.scientificName}>{plant.scientific_name}</Text>
          {plant.malay_name && <Text style={styles.malayName}>{plant.malay_name}</Text>}
        </View>

        {/* Description box */}
        {plant.description && (
          <View style={styles.descBox}>
            <Text style={styles.descText}>{plant.description}</Text>
          </View>
        )}

        {/* Community photos */}
        {communityPhotos.length > 1 && (
          <>
            <Text style={styles.sectionLabel}>COMMUNITY PHOTOS</Text>
            <View style={styles.photoGrid}>
              {communityPhotos.slice(1).map((p, i) => (
                <Image key={i} source={{ uri: p.photo_url }} style={styles.gridPhoto} />
              ))}
            </View>
          </>
        )}

        {plant.wikipedia_url && (
          <Text style={styles.wikiLink}>🔗 Wikipedia</Text>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.contentBg },
  infoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.primary,
    paddingTop: Platform.OS === 'ios' ? 52 : 16,
    paddingBottom: 8,
    paddingHorizontal: 14,
  },
  backBtn: { flex: 1 },
  infoHeaderTitle: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '800',
    fontFamily: mono,
    letterSpacing: 1,
  },
  flBadge: {
    backgroundColor: Colors.sidebarBg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 0,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderTopColor: 'rgba(255,255,255,0.4)',
    borderLeftColor: 'rgba(255,255,255,0.4)',
    borderBottomColor: 'rgba(0,0,0,0.4)',
    borderRightColor: 'rgba(0,0,0,0.4)',
  },
  flBadgeText: { color: '#ffffff', fontWeight: '800', fontSize: 13, fontFamily: mono },
  loadingArea: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loading: { color: Colors.darkTextMuted, fontSize: 14, fontFamily: mono },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 40 },

  // Top panel
  topPanel: {
    flexDirection: 'row',
    backgroundColor: Colors.contentBg,
    padding: 10,
    gap: 10,
    borderBottomWidth: 2,
    borderBottomColor: Colors.gridLine,
  },
  imageBox: {
    width: 160,
    height: 180,
    backgroundColor: Colors.infoBoxBg,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: Colors.pixelShadow,
    borderLeftColor: Colors.pixelShadow,
    borderBottomColor: Colors.pixelHighlight,
    borderRightColor: Colors.pixelHighlight,
    overflow: 'hidden',
  },
  plantImage: { width: '100%', height: '100%', resizeMode: 'cover' },
  imagePlaceholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#E8E8E8',
  },
  placeholderEmoji: { fontSize: 60 },

  // Info box (right)
  infoBox: {
    flex: 1,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: Colors.infoBoxBorder,
    borderLeftColor: Colors.infoBoxBorder,
    borderBottomColor: '#8B0000',
    borderRightColor: '#8B0000',
    backgroundColor: Colors.infoBoxBg,
  },
  infoRow: {
    padding: 6,
  },
  infoDivider: {
    height: 1,
    backgroundColor: Colors.dotLineColor,
    marginHorizontal: 4,
    borderStyle: 'dotted',
    borderBottomWidth: 1,
    borderBottomColor: Colors.dotLineColor,
  },
  infoNumName: {
    fontSize: 11,
    fontWeight: '800',
    color: Colors.darkText,
    fontFamily: mono,
    lineHeight: 15,
  },
  stars: {
    fontSize: 14,
    color: Colors.infoBoxBorder,
    letterSpacing: 1,
  },
  statLine: { fontSize: 10, fontFamily: mono },
  statKey: { color: Colors.darkTextMuted, fontWeight: '700' },
  statVal: { color: Colors.darkText, fontWeight: '700' },

  // Pioneer banner
  pioneerBanner: {
    backgroundColor: Colors.accent + '33',
    borderLeftWidth: 4,
    borderLeftColor: Colors.accent,
    padding: 10,
    marginHorizontal: 10,
    marginTop: 8,
  },
  pioneerText: { color: '#8B6914', fontWeight: '700', fontSize: 12, fontFamily: mono },

  // Names
  namesBox: {
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 6,
  },
  scientificName: {
    color: Colors.darkText,
    fontSize: 17,
    fontWeight: '700',
    fontStyle: 'italic',
  },
  malayName: { color: Colors.darkTextMuted, fontSize: 13, marginTop: 2 },

  // Description box
  descBox: {
    marginHorizontal: 10,
    marginBottom: 10,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: Colors.infoBoxBorder,
    borderLeftColor: Colors.infoBoxBorder,
    borderBottomColor: '#8B0000',
    borderRightColor: '#8B0000',
    backgroundColor: Colors.infoBoxBg,
    padding: 12,
  },
  descText: {
    color: Colors.darkText,
    fontSize: 13,
    lineHeight: 20,
    fontFamily: mono,
  },

  // Community photos
  sectionLabel: {
    color: Colors.darkTextMuted,
    fontSize: 10,
    fontFamily: mono,
    letterSpacing: 1.5,
    paddingHorizontal: 12,
    marginBottom: 6,
    marginTop: 4,
  },
  photoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 10,
    gap: 4,
    marginBottom: 8,
  },
  gridPhoto: { width: '31%', aspectRatio: 1, borderRadius: 0 },
  wikiLink: { color: Colors.primary, paddingHorizontal: 12, marginBottom: 12, fontFamily: mono },
});
