import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, TouchableOpacity,
  TextInput, SafeAreaView, RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { getAllPlants, type Plant } from '../../src/supabase/plants';
import { getUserDiscoveredPlantIds } from '../../src/supabase/discoveries';
import { supabase } from '../../src/supabase/client';
import { useAuthStore } from '../../src/store/authStore';
import { useGameStore } from '../../src/store/gameStore';
import { Colors } from '../../src/constants/colors';
import { LEVEL_TITLES, LEVEL_THRESHOLDS } from '../../src/store/gameStore';
import PlantCard from '../../src/components/PlantCard';

type Filter = 'all' | 'mine' | 'undiscovered';

export default function FloradexScreen() {
  const router = useRouter();
  const { session } = useAuthStore();
  const { totalXp, level, pioneerCount, discoveredPlantIds } = useGameStore();
  const [plants, setPlants] = useState<Plant[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [pioneerDiscoveryIds, setPioneerDiscoveryIds] = useState<Set<string>>(new Set());
  const [userPhotoUrls, setUserPhotoUrls] = useState<Record<string, string>>({});

  async function loadData() {
    const allPlants = await getAllPlants();
    setPlants(allPlants);

    if (session?.user) {
      const { data } = await supabase
        .from('discoveries')
        .select('plant_id, is_pioneer, photo_url')
        .eq('user_id', session.user.id);

      if (data) {
        const pioneers = new Set(data.filter((d) => d.is_pioneer).map((d) => d.plant_id));
        setPioneerDiscoveryIds(pioneers);
        const photos: Record<string, string> = {};
        data.forEach((d) => { if (d.photo_url) photos[d.plant_id] = d.photo_url; });
        setUserPhotoUrls(photos);
      }
    }
  }

  useEffect(() => { loadData(); }, [session?.user?.id]);

  async function handleRefresh() {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }

  const filtered = plants.filter((p) => {
    const isDiscovered = discoveredPlantIds.has(p.id);
    if (filter === 'mine' && !isDiscovered) return false;
    if (filter === 'undiscovered' && isDiscovered) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        p.scientific_name.toLowerCase().includes(q) ||
        (p.common_name?.toLowerCase().includes(q) ?? false)
      );
    }
    return true;
  });

  const nextLevelXp = LEVEL_THRESHOLDS[level] ?? LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1];
  const currentLevelXp = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const progress = nextLevelXp > currentLevelXp
    ? (totalXp - currentLevelXp) / (nextLevelXp - currentLevelXp)
    : 1;

  return (
    <SafeAreaView style={styles.container}>
      {/* Header with XP */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Floradex</Text>
          <Text style={styles.subtitle}>
            {discoveredPlantIds.size}/{plants.length} species · {pioneerCount} pioneered
          </Text>
        </View>
        <View style={styles.levelBadge}>
          <Text style={styles.levelNum}>Lv.{level}</Text>
          <Text style={styles.levelTitle}>{LEVEL_TITLES[level - 1]}</Text>
        </View>
      </View>

      {/* XP Progress bar */}
      <View style={styles.xpBarBg}>
        <View style={[styles.xpBarFill, { width: `${Math.min(progress * 100, 100)}%` }]} />
      </View>
      <Text style={styles.xpText}>{totalXp} XP</Text>

      {/* Search */}
      <TextInput
        style={styles.search}
        placeholder="Search plants..."
        placeholderTextColor={Colors.textMuted}
        value={search}
        onChangeText={setSearch}
      />

      {/* Filter tabs */}
      <View style={styles.filters}>
        {(['all', 'mine', 'undiscovered'] as Filter[]).map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterBtn, filter === f && styles.filterActive]}
            onPress={() => setFilter(f)}
          >
            <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>
              {f === 'all' ? 'All' : f === 'mine' ? 'My Collection' : 'Undiscovered'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Plant grid */}
      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={styles.row}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={Colors.primary} />}
        renderItem={({ item }) => (
          <View style={styles.cardWrapper}>
            <PlantCard
              plant={item}
              discovered={discoveredPlantIds.has(item.id)}
              isPioneer={pioneerDiscoveryIds.has(item.id)}
              photoUrl={userPhotoUrls[item.id]}
              onPress={() => router.push(`/plant/${item.id}`)}
            />
          </View>
        )}
        ListEmptyComponent={
          <Text style={styles.empty}>
            {plants.length === 0 ? 'No plants discovered yet. Go explore! 🌿' : 'No results found.'}
          </Text>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  title: { color: Colors.text, fontSize: 26, fontWeight: '800' },
  subtitle: { color: Colors.textMuted, fontSize: 13, marginTop: 2 },
  levelBadge: {
    backgroundColor: Colors.surface,
    borderRadius: 12,
    padding: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  levelNum: { color: Colors.primary, fontWeight: '800', fontSize: 16 },
  levelTitle: { color: Colors.textMuted, fontSize: 10, marginTop: 2 },
  xpBarBg: {
    height: 4,
    backgroundColor: Colors.surface,
    marginHorizontal: 16,
    borderRadius: 2,
    overflow: 'hidden',
  },
  xpBarFill: { height: '100%', backgroundColor: Colors.primary },
  xpText: { color: Colors.textMuted, fontSize: 11, textAlign: 'right', marginHorizontal: 16, marginTop: 2 },
  search: {
    backgroundColor: Colors.surface,
    color: Colors.text,
    borderRadius: 10,
    padding: 10,
    marginHorizontal: 16,
    marginTop: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    fontSize: 14,
  },
  filters: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginTop: 10,
    gap: 8,
  },
  filterBtn: {
    flex: 1,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: Colors.surface,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  filterActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  filterText: { color: Colors.textMuted, fontSize: 12, fontWeight: '600' },
  filterTextActive: { color: Colors.background },
  list: { padding: 16 },
  row: { gap: 12 },
  cardWrapper: { flex: 1 },
  empty: { color: Colors.textMuted, textAlign: 'center', marginTop: 40, fontSize: 15 },
});
