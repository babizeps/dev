import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, TouchableOpacity,
  TextInput, Platform, RefreshControl, Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { getAllPlants, type Plant } from '../../src/supabase/plants';
import { supabase } from '../../src/supabase/client';
import { useAuthStore } from '../../src/store/authStore';
import { useGameStore } from '../../src/store/gameStore';
import { Colors } from '../../src/constants/colors';
import { LEVEL_TITLES, LEVEL_THRESHOLDS } from '../../src/store/gameStore';
import PlantCard from '../../src/components/PlantCard';
import { PokedexHeader } from '../../src/components/PokedexHeader';

const SCREEN_WIDTH = Dimensions.get('window').width;
const SIDEBAR_WIDTH = 28;
const NUM_COLUMNS = 4;
const mono = Platform.OS === 'ios' ? 'Courier New' : 'monospace';

type Filter = 'all' | 'mine' | 'undiscovered';

function LevelBadge({ level, title }: { level: number; title: string }) {
  return (
    <View style={styles.levelBadge}>
      <Text style={styles.levelNum}>Lv.{level}</Text>
      <Text style={styles.levelTitle}>{title}</Text>
    </View>
  );
}

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
  const [selectedPlantId, setSelectedPlantId] = useState<string | null>(null);

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

  const selectedPlant = selectedPlantId ? filtered.find(p => p.id === selectedPlantId) : null;
  const selectedIndex = selectedPlantId ? filtered.findIndex(p => p.id === selectedPlantId) : -1;

  return (
    <View style={styles.container}>
      <PokedexHeader
        title="Floradex"
        subtitle={`${discoveredPlantIds.size}/${plants.length} species · ${pioneerCount} ★`}
        rightSlot={<LevelBadge level={level} title={LEVEL_TITLES[level - 1]} />}
      />

      {/* Search + filters */}
      <View style={styles.controls}>
        <TextInput
          style={styles.search}
          placeholder="Search..."
          placeholderTextColor={Colors.darkTextMuted}
          value={search}
          onChangeText={setSearch}
        />
        <View style={styles.filters}>
          {(['all', 'mine', 'undiscovered'] as Filter[]).map((f) => (
            <TouchableOpacity
              key={f}
              style={[styles.filterBtn, filter === f && styles.filterActive]}
              onPress={() => setFilter(f)}
            >
              <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>
                {f === 'all' ? 'ALL' : f === 'mine' ? 'MY DEX' : 'UNSEEN'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Main area: sidebar + grid */}
      <View style={styles.mainArea}>
        {/* Left sidebar */}
        <View style={styles.sidebar}>
          <Text style={styles.sidebarText}>F{'\n'}L{'\n'}O{'\n'}R{'\n'}A</Text>
        </View>

        {/* Plant grid */}
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          numColumns={NUM_COLUMNS}
          style={styles.grid}
          contentContainerStyle={styles.gridContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={Colors.primary} />}
          renderItem={({ item, index }) => (
            <PlantCard
              plant={item}
              discovered={discoveredPlantIds.has(item.id)}
              isPioneer={pioneerDiscoveryIds.has(item.id)}
              photoUrl={userPhotoUrls[item.id]}
              entryIndex={index + 1}
              selected={item.id === selectedPlantId}
              onPress={() => {
                setSelectedPlantId(item.id);
                router.push(`/plant/${item.id}`);
              }}
            />
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>
              {plants.length === 0 ? 'No plants yet. Go explore!' : 'No results.'}
            </Text>
          }
        />

        {/* Right scrollbar (decorative) */}
        <View style={styles.scrollbarTrack}>
          <View style={styles.scrollbarThumb} />
        </View>
      </View>

      {/* Status bar */}
      <View style={styles.statusBar}>
        <Text style={styles.statusText}>
          {selectedPlant
            ? `${String(selectedIndex + 1).padStart(3, '0')}  ${(selectedPlant.common_name ?? selectedPlant.scientific_name).toUpperCase()}`
            : '— FLORADEX —'}
        </Text>
      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  levelBadge: {
    backgroundColor: Colors.sidebarBg,
    borderRadius: 0,
    paddingHorizontal: 10,
    paddingVertical: 6,
    alignItems: 'center',
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: 'rgba(255,255,255,0.45)',
    borderLeftColor: 'rgba(255,255,255,0.45)',
    borderBottomColor: 'rgba(0,0,0,0.5)',
    borderRightColor: 'rgba(0,0,0,0.5)',
  },
  levelNum: { color: '#ffffff', fontWeight: '900', fontSize: 15, fontFamily: mono },
  levelTitle: { color: 'rgba(255,255,255,0.85)', fontSize: 9, marginTop: 2, letterSpacing: 1, fontFamily: mono },
  xpBarBg: { height: 5, backgroundColor: Colors.surface, overflow: 'hidden' },
  xpBarFill: { height: '100%', backgroundColor: Colors.primary },
  controls: {
    backgroundColor: Colors.contentBg,
    paddingHorizontal: 8,
    paddingTop: 6,
    paddingBottom: 4,
    borderBottomWidth: 3,
    borderBottomColor: Colors.sidebarBg,
  },
  search: {
    backgroundColor: Colors.infoBoxBg,
    color: Colors.darkText,
    borderRadius: 0,
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderTopColor: Colors.pixelShadow,
    borderLeftColor: Colors.pixelShadow,
    borderBottomColor: Colors.pixelHighlight,
    borderRightColor: Colors.pixelHighlight,
    fontSize: 12,
    fontFamily: mono,
    marginBottom: 5,
  },
  filters: { flexDirection: 'row', gap: 4 },
  filterBtn: {
    flex: 1,
    paddingVertical: 4,
    borderRadius: 0,
    backgroundColor: Colors.infoBoxBg,
    alignItems: 'center',
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderTopColor: Colors.pixelHighlight,
    borderLeftColor: Colors.pixelHighlight,
    borderBottomColor: Colors.pixelShadow,
    borderRightColor: Colors.pixelShadow,
  },
  filterActive: {
    backgroundColor: Colors.primary,
    borderTopColor: Colors.pixelShadow,
    borderLeftColor: Colors.pixelShadow,
    borderBottomColor: Colors.pixelHighlight,
    borderRightColor: Colors.pixelHighlight,
  },
  filterText: { color: Colors.darkTextMuted, fontSize: 10, fontWeight: '700', letterSpacing: 0.5, fontFamily: mono },
  filterTextActive: { color: '#ffffff' },
  mainArea: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: Colors.contentBg,
  },
  sidebar: {
    width: SIDEBAR_WIDTH,
    backgroundColor: Colors.sidebarBg,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 8,
  },
  sidebarText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 8,
    fontWeight: '700',
    textAlign: 'center',
    letterSpacing: 2,
    lineHeight: 12,
    fontFamily: mono,
  },
  grid: { flex: 1 },
  gridContent: { flexGrow: 1 },
  scrollbarTrack: {
    width: 10,
    backgroundColor: '#C8C8C8',
    marginVertical: 0,
    borderRadius: 0,
    borderLeftWidth: 1,
    borderLeftColor: Colors.pixelShadow,
  },
  scrollbarThumb: {
    width: '100%',
    height: 40,
    backgroundColor: '#4488CC',
    borderRadius: 0,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopColor: '#88BBEE',
    borderLeftColor: '#88BBEE',
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderBottomColor: '#224477',
    borderRightColor: '#224477',
  },
  statusBar: {
    height: 28,
    backgroundColor: Colors.statusBarBg,
    justifyContent: 'center',
    paddingHorizontal: 10,
    borderTopWidth: 3,
    borderTopColor: Colors.primary,
  },
  statusText: {
    color: '#ffffff',
    fontSize: 12,
    fontFamily: mono,
    fontWeight: '700',
    letterSpacing: 1,
  },
  actionBar: {
    flexDirection: 'row',
    backgroundColor: '#555555',
    paddingVertical: 5,
    paddingHorizontal: 8,
    justifyContent: 'space-around',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#444444',
  },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  btnCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnLetter: { color: '#ffffff', fontSize: 9, fontWeight: '800', fontFamily: mono },
  btnLabel: { color: '#cccccc', fontSize: 9, fontFamily: mono, letterSpacing: 0.5 },
  empty: { color: Colors.darkTextMuted, textAlign: 'center', marginTop: 40, fontSize: 13 },
});
