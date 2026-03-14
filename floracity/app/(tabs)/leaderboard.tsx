import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, RefreshControl, Platform,
} from 'react-native';
import { getLeaderboard, subscribeToLeaderboard, type LeaderboardEntry } from '../../src/supabase/leaderboard';
import { useAuthStore } from '../../src/store/authStore';
import { Colors } from '../../src/constants/colors';
import { LEVEL_TITLES } from '../../src/store/gameStore';
import { PokedexHeader } from '../../src/components/PokedexHeader';

const mono = Platform.OS === 'ios' ? 'Courier New' : 'monospace';

export default function LeaderboardScreen() {
  const { session } = useAuthStore();
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    getLeaderboard().then(setEntries);
    const unsubscribe = subscribeToLeaderboard(setEntries);
    return () => { unsubscribe(); };
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    const data = await getLeaderboard();
    setEntries(data);
    setRefreshing(false);
  }

  function renderRow({ item, index }: { item: LeaderboardEntry; index: number }) {
    const isMe = item.id === session?.user?.id;
    const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : null;

    return (
      <View style={[styles.row, isMe && styles.rowMe]}>
        <Text style={[styles.rank, { fontFamily: mono }]}>{medal ?? `#${index + 1}`}</Text>
        <View style={styles.info}>
          <Text style={styles.username}>{item.username ?? 'Explorer'}{isMe ? ' (you)' : ''}</Text>
          <Text style={styles.sub}>
            Lv.{item.level} {LEVEL_TITLES[item.level - 1]} · {item.species_count} species · {item.pioneer_count} ⭐
          </Text>
        </View>
        <Text style={[styles.xp, { fontFamily: mono }]}>{item.total_xp.toLocaleString()} XP</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <PokedexHeader title="Rankings" subtitle="Top explorers of Forest City" />
      <FlatList
        data={entries}
        keyExtractor={(item) => item.id}
        renderItem={renderRow}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={Colors.primary} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>No explorers yet — be the first! 🌿</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  list: { padding: 16 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 0,
    padding: 14,
    marginBottom: 4,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderTopColor: '#333333',
    borderLeftColor: '#333333',
    borderBottomColor: '#111111',
    borderRightColor: '#111111',
  },
  rowMe: {
    borderTopColor: Colors.primary,
    borderLeftColor: Colors.primary,
    borderBottomColor: '#8B0000',
    borderRightColor: '#8B0000',
    backgroundColor: Colors.surface,
  },
  rank: { width: 36, fontSize: 18, textAlign: 'center', color: Colors.text },
  info: { flex: 1, marginLeft: 8 },
  username: { color: Colors.text, fontWeight: '700', fontSize: 15 },
  sub: { color: Colors.textMuted, fontSize: 12, marginTop: 2 },
  xp: { color: Colors.primary, fontWeight: '700', fontSize: 13 },
  empty: { color: Colors.textMuted, textAlign: 'center', marginTop: 40 },
});
