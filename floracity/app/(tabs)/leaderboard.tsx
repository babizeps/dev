import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, SafeAreaView, RefreshControl,
} from 'react-native';
import { getLeaderboard, subscribeToLeaderboard, type LeaderboardEntry } from '../../src/supabase/leaderboard';
import { useAuthStore } from '../../src/store/authStore';
import { Colors } from '../../src/constants/colors';
import { LEVEL_TITLES } from '../../src/store/gameStore';

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
        <Text style={styles.rank}>{medal ?? `#${index + 1}`}</Text>
        <View style={styles.info}>
          <Text style={styles.username}>{item.username ?? 'Explorer'}{isMe ? ' (you)' : ''}</Text>
          <Text style={styles.sub}>
            Lv.{item.level} {LEVEL_TITLES[item.level - 1]} · {item.species_count} species · {item.pioneer_count} ⭐
          </Text>
        </View>
        <Text style={styles.xp}>{item.total_xp.toLocaleString()} XP</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>🏆 Rankings</Text>
      <Text style={styles.sub2}>Top explorers of Forest City</Text>
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
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  title: { color: Colors.text, fontSize: 26, fontWeight: '800', padding: 16, paddingBottom: 4 },
  sub2: { color: Colors.textMuted, fontSize: 13, paddingHorizontal: 16, marginBottom: 8 },
  list: { padding: 16 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  rowMe: {
    borderColor: Colors.primary,
    backgroundColor: Colors.surface,
  },
  rank: { width: 36, fontSize: 20, textAlign: 'center' },
  info: { flex: 1, marginLeft: 8 },
  username: { color: Colors.text, fontWeight: '700', fontSize: 15 },
  sub: { color: Colors.textMuted, fontSize: 12, marginTop: 2 },
  xp: { color: Colors.primary, fontWeight: '700', fontSize: 14 },
  empty: { color: Colors.textMuted, textAlign: 'center', marginTop: 40 },
});
