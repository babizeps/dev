import { useEffect, useState } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { supabase } from '../src/supabase/client';
import { useAuthStore } from '../src/store/authStore';
import { useGameStore } from '../src/store/gameStore';
import { getUserDiscoveredPlantIds } from '../src/supabase/discoveries';
import {
  MOCK_USER_ID, MOCK_DISCOVERED_IDS, MOCK_PIONEER_IDS,
} from '../src/mock/data';

const MOCK_MODE = process.env.EXPO_PUBLIC_MOCK_MODE === 'true';

// Fake session object used in mock mode
const MOCK_SESSION = {
  user: { id: MOCK_USER_ID, email: 'test@floracity.app' },
  access_token: 'mock-token',
} as any;

export default function RootLayout() {
  const { session, setSession } = useAuthStore();
  const { setProfile, setDiscoveredPlantIds } = useGameStore();
  const router = useRouter();
  const segments = useSegments();
  const [isMounted, setIsMounted] = useState(false);

  // Mark navigator as ready after first render
  useEffect(() => { setIsMounted(true); }, []);

  useEffect(() => {
    if (MOCK_MODE) {
      setSession(MOCK_SESSION);
      setProfile(125, 2, 2);
      setDiscoveredPlantIds(MOCK_DISCOVERED_IDS);
      return;
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Load user profile and discoveries after auth (real mode only)
  useEffect(() => {
    if (MOCK_MODE || !session?.user) return;

    supabase
      .from('profiles')
      .select('total_xp, level, pioneer_count')
      .eq('id', session.user.id)
      .single()
      .then(({ data }) => {
        if (data) setProfile(data.total_xp, data.level, data.pioneer_count);
      });

    getUserDiscoveredPlantIds(session.user.id).then(setDiscoveredPlantIds);
  }, [session?.user?.id]);

  // Auth guard — only navigate after first render (navigator is mounted)
  useEffect(() => {
    if (!isMounted) return;
    const inAuthGroup = segments[0] === 'auth';
    if (!session && !inAuthGroup) {
      router.replace('/auth/login');
    } else if (session && inAuthGroup) {
      router.replace('/(tabs)/');
    }
  }, [session, segments, isMounted]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack screenOptions={{ headerShown: false }} />
    </GestureHandlerRootView>
  );
}
