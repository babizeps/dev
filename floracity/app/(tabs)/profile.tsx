import { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  ScrollView, Alert, Platform,
} from 'react-native';
import { supabase } from '../../src/supabase/client';
import { useAuthStore } from '../../src/store/authStore';
import { useGameStore, LEVEL_TITLES, LEVEL_THRESHOLDS } from '../../src/store/gameStore';
import { Colors } from '../../src/constants/colors';
import { ACHIEVEMENTS } from '../../src/constants/achievements';
import { PokedexHeader } from '../../src/components/PokedexHeader';

const MOCK_MODE = process.env.EXPO_PUBLIC_MOCK_MODE === 'true';
const mono = Platform.OS === 'ios' ? 'Courier New' : 'monospace';

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

  const initials = username ? username[0].toUpperCase() : '?';

  return (
    <View style={styles.container}>
      <PokedexHeader title="Profile" />
      <ScrollView contentContainerStyle={styles.content}>
        {/* Avatar */}
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.username}>{username || 'Explorer'}</Text>

        {/* Level badge */}
        <View style={styles.levelBadge}>
          <Text style={styles.levelBadgeText}>{LEVEL_TITLES[level - 1]}  ·  Level {level}</Text>
        </View>

        {/* XP Bar */}
        <View style={styles.xpBarBg}>
          <View style={[styles.xpBarFill, { width: `${Math.min(progress * 100, 100)}%` }]} />
        </View>
        <Text style={styles.xpText}>{totalXp} / {nextLevelXp} XP</Text>

        {/* Stats panel - LCD style */}
        <View style={styles.statsPanel}>
          <View style={styles.stat}>
            <Text style={styles.statNum}>{discoveredPlantIds.size}</Text>
            <Text style={styles.statLabel}>SPECIES</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statNum}>{pioneerCount}</Text>
            <Text style={styles.statLabel}>PIONEERED ⭐</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statNum}>{totalXp.toLocaleString()}</Text>
            <Text style={styles.statLabel}>TOTAL XP</Text>
          </View>
        </View>

        {/* Achievements */}
        <Text style={styles.sectionTitle}>ACHIEVEMENTS</Text>
        {ACHIEVEMENTS.map((a) => {
          const unlocked = unlockedKeys.has(a.key);
          return (
            <View key={a.key} style={[styles.achievRow, unlocked && styles.achievUnlocked, !unlocked && styles.achievLocked]}>
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: 24, alignItems: 'center' },
  avatarCircle: {
    width: 80,
    height: 80,
    borderRadius: 0,
    backgroundColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    marginTop: 8,
    borderTopWidth: 4,
    borderLeftWidth: 4,
    borderBottomWidth: 4,
    borderRightWidth: 4,
    borderTopColor: Colors.pixelBtnHighlight,
    borderLeftColor: Colors.pixelBtnHighlight,
    borderBottomColor: Colors.pixelBtnShadow,
    borderRightColor: Colors.pixelBtnShadow,
  },
  avatarText: { color: '#ffffff', fontSize: 32, fontWeight: '800' },
  username: { color: Colors.text, fontSize: 22, fontWeight: '800' },
  levelBadge: {
    borderRadius: 0,
    paddingHorizontal: 12,
    paddingVertical: 5,
    marginTop: 8,
    marginBottom: 16,
    backgroundColor: Colors.primary + '22',
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderTopColor: Colors.pixelBtnHighlight,
    borderLeftColor: Colors.pixelBtnHighlight,
    borderBottomColor: Colors.pixelBtnShadow,
    borderRightColor: Colors.pixelBtnShadow,
  },
  levelBadgeText: { color: Colors.primary, fontSize: 13, fontWeight: '700', letterSpacing: 0.5 },
  xpBarBg: {
    width: '100%',
    height: 8,
    backgroundColor: Colors.surface,
    borderRadius: 0,
    overflow: 'hidden',
  },
  xpBarFill: { height: '100%', backgroundColor: Colors.primary },
  xpText: {
    color: Colors.textMuted,
    fontSize: 11,
    marginTop: 4,
    marginBottom: 20,
    fontFamily: mono,
    alignSelf: 'flex-end',
  },
  statsPanel: {
    flexDirection: 'row',
    backgroundColor: Colors.screenBg,
    borderRadius: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: Colors.pixelShadow,
    borderLeftColor: Colors.pixelShadow,
    borderBottomColor: '#111111',
    borderRightColor: '#111111',
    width: '100%',
    marginBottom: 24,
    overflow: 'hidden',
  },
  stat: { flex: 1, alignItems: 'center', paddingVertical: 14 },
  statNum: {
    color: Colors.screenText,
    fontSize: 20,
    fontWeight: '800',
    fontFamily: mono,
  },
  statLabel: {
    color: Colors.screenDim,
    fontSize: 9,
    marginTop: 3,
    fontFamily: mono,
    letterSpacing: 0.8,
    textAlign: 'center',
  },
  statDivider: { width: 1, backgroundColor: Colors.screenDim },
  sectionTitle: {
    color: Colors.textMuted,
    fontSize: 10,
    fontFamily: mono,
    letterSpacing: 1.5,
    alignSelf: 'flex-start',
    marginBottom: 10,
  },
  achievRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderRadius: 0,
    padding: 12,
    width: '100%',
    marginBottom: 6,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderTopColor: '#333333',
    borderLeftColor: '#333333',
    borderBottomColor: '#111111',
    borderRightColor: '#111111',
    gap: 12,
  },
  achievUnlocked: {
    borderLeftWidth: 4,
    borderLeftColor: Colors.primary,
  },
  achievLocked: { opacity: 0.5 },
  achievIcon: { fontSize: 22 },
  achievName: { color: Colors.text, fontWeight: '700', fontSize: 14 },
  textDim: { color: Colors.textDim },
  achievDesc: { color: Colors.textMuted, fontSize: 12, marginTop: 2 },
  signOutBtn: {
    marginTop: 28,
    padding: 14,
    borderRadius: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: '#FF8888',
    borderLeftColor: '#FF8888',
    borderBottomColor: '#880000',
    borderRightColor: '#880000',
    width: '100%',
    alignItems: 'center',
    backgroundColor: '#1a0505',
  },
  signOutText: { color: Colors.error, fontWeight: '700' },
});
