import { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, SafeAreaView, TouchableOpacity,
  ScrollView, Alert,
} from 'react-native';
import { supabase } from '../../src/supabase/client';
import { useAuthStore } from '../../src/store/authStore';
import { useGameStore, LEVEL_TITLES, LEVEL_THRESHOLDS } from '../../src/store/gameStore';
import { Colors } from '../../src/constants/colors';
import { ACHIEVEMENTS } from '../../src/constants/achievements';

const MOCK_MODE = process.env.EXPO_PUBLIC_MOCK_MODE === 'true';

type UnlockedAchievement = { achievement_key: string; unlocked_at: string };

export default function ProfileScreen() {
  const { session } = useAuthStore();
  const { totalXp, level, pioneerCount, discoveredPlantIds } = useGameStore();
  const [unlockedAchievements, setUnlockedAchievements] = useState<UnlockedAchievement[]>(
    MOCK_MODE ? [{ achievement_key: 'first_bloom', unlocked_at: '' }, { achievement_key: 'pioneer', unlocked_at: '' }] : []
  );
  const [username, setUsername] = useState(MOCK_MODE ? 'TestExplorer' : '');

  useEffect(() => {
    if (MOCK_MODE || !session?.user) return;
    supabase
      .from('profiles')
      .select('username')
      .eq('id', session.user.id)
      .single()
      .then(({ data }) => { if (data?.username) setUsername(data.username); });

    supabase
      .from('achievements')
      .select('achievement_key, unlocked_at')
      .eq('user_id', session.user.id)
      .then(({ data }) => setUnlockedAchievements(data ?? []));
  }, [session?.user?.id]);

  const unlockedKeys = new Set(unlockedAchievements.map((a) => a.achievement_key));
  const nextLevelXp = LEVEL_THRESHOLDS[level] ?? LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1];
  const currentLevelXp = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const progress = nextLevelXp > currentLevelXp
    ? (totalXp - currentLevelXp) / (nextLevelXp - currentLevelXp) : 1;

  async function handleSignOut() {
    Alert.alert('Sign Out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: () => supabase.auth.signOut() },
    ]);
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.emoji}>🌱</Text>
        <Text style={styles.username}>{username || 'Explorer'}</Text>
        <Text style={styles.levelTitle}>{LEVEL_TITLES[level - 1]} · Level {level}</Text>

        <View style={styles.xpBarBg}>
          <View style={[styles.xpBarFill, { width: `${Math.min(progress * 100, 100)}%` }]} />
        </View>
        <Text style={styles.xpText}>{totalXp} / {nextLevelXp} XP</Text>

        {/* Stats */}
        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statNum}>{discoveredPlantIds.size}</Text>
            <Text style={styles.statLabel}>Species Found</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statNum}>{pioneerCount}</Text>
            <Text style={styles.statLabel}>Pioneered ⭐</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statNum}>{totalXp.toLocaleString()}</Text>
            <Text style={styles.statLabel}>Total XP</Text>
          </View>
        </View>

        {/* Achievements */}
        <Text style={styles.sectionTitle}>Achievements</Text>
        {ACHIEVEMENTS.map((a) => {
          const unlocked = unlockedKeys.has(a.key);
          return (
            <View key={a.key} style={[styles.achievRow, !unlocked && styles.achievLocked]}>
              <Text style={styles.achievIcon}>{unlocked ? a.icon : '🔒'}</Text>
              <View style={{ flex: 1 }}>
                <Text style={[styles.achievName, !unlocked && styles.textDim]}>{a.name}</Text>
                <Text style={styles.achievDesc}>{a.description}</Text>
              </View>
            </View>
          );
        })}

        <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
          <Text style={styles.signOutText}>Sign Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: 24, alignItems: 'center' },
  emoji: { fontSize: 64, marginBottom: 8 },
  username: { color: Colors.text, fontSize: 24, fontWeight: '800' },
  levelTitle: { color: Colors.primary, fontSize: 14, marginTop: 4, marginBottom: 16 },
  xpBarBg: {
    width: '100%',
    height: 8,
    backgroundColor: Colors.surface,
    borderRadius: 4,
    overflow: 'hidden',
  },
  xpBarFill: { height: '100%', backgroundColor: Colors.primary, borderRadius: 4 },
  xpText: { color: Colors.textMuted, fontSize: 12, marginTop: 4, marginBottom: 24 },
  statsRow: {
    flexDirection: 'row',
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 16,
    width: '100%',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  stat: { flex: 1, alignItems: 'center' },
  statNum: { color: Colors.text, fontSize: 22, fontWeight: '800' },
  statLabel: { color: Colors.textMuted, fontSize: 11, marginTop: 4, textAlign: 'center' },
  statDivider: { width: 1, backgroundColor: Colors.border },
  sectionTitle: {
    color: Colors.text,
    fontSize: 18,
    fontWeight: '700',
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  achievRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 12,
    padding: 12,
    width: '100%',
    marginBottom: 8,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 12,
  },
  achievLocked: { opacity: 0.5 },
  achievIcon: { fontSize: 24 },
  achievName: { color: Colors.text, fontWeight: '700', fontSize: 14 },
  textDim: { color: Colors.textDim },
  achievDesc: { color: Colors.textMuted, fontSize: 12, marginTop: 2 },
  signOutBtn: {
    marginTop: 32,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.error,
    width: '100%',
    alignItems: 'center',
  },
  signOutText: { color: Colors.error, fontWeight: '700' },
});
