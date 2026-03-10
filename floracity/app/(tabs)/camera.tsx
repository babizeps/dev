import { useState, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator,
  Alert, Modal, ScrollView, Image,
} from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import * as Location from 'expo-location';
import Animated, {
  useSharedValue, useAnimatedStyle, withRepeat, withTiming,
  withSequence, Easing,
} from 'react-native-reanimated';
import { supabase } from '../../src/supabase/client';
import { useAuthStore } from '../../src/store/authStore';
import { useGameStore } from '../../src/store/gameStore';
import { Colors } from '../../src/constants/colors';
import XPPopup from '../../src/components/XPPopup';
import { MOCK_PLANTS, MOCK_DISCOVERED_IDS } from '../../src/mock/data';

const MOCK_MODE = process.env.EXPO_PUBLIC_MOCK_MODE === 'true';

type Suggestion = {
  scientific_name: string;
  common_name: string | null;
  family: string | null;
  description: string | null;
  wikipedia_url: string | null;
  confidence: number;
};

type DiscoveryResult = {
  plant_id: string;
  plant: Suggestion;
  xp_gained: number;
  is_pioneer: boolean;
  photo_url: string;
  already_discovered: boolean;
  needs_confirmation?: boolean;
  suggestions?: Suggestion[];
};

export default function CameraScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<DiscoveryResult | null>(null);
  const [confirmSuggestions, setConfirmSuggestions] = useState<Suggestion[] | null>(null);
  const cameraRef = useRef<CameraView>(null);
  const { session } = useAuthStore();
  const { addDiscovery } = useGameStore();

  // Scan line animation
  const scanY = useSharedValue(0);
  const scanStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: scanY.value }],
  }));

  function startScanAnimation() {
    scanY.value = withRepeat(
      withSequence(
        withTiming(280, { duration: 1500, easing: Easing.linear }),
        withTiming(0, { duration: 0 })
      ),
      -1
    );
  }

  async function handleCapture() {
    if (!session?.user) return;

    setScanning(true);
    startScanAnimation();

    try {
      // Mock mode: simulate a 2s scan + random plant discovery
      if (MOCK_MODE) {
        await new Promise((r) => setTimeout(r, 2000));
        const undiscovered = MOCK_PLANTS.filter((p) => !MOCK_DISCOVERED_IDS.has(p.id));
        const pick = undiscovered[Math.floor(Math.random() * undiscovered.length)] ?? MOCK_PLANTS[0];
        const isPioneer = pick.first_discovered_by === null;
        const data = {
          plant_id: pick.id,
          plant: {
            scientific_name: pick.scientific_name,
            common_name: pick.common_name,
            family: pick.family,
            description: pick.description,
            wikipedia_url: pick.wikipedia_url,
            confidence: 0.94,
          },
          xp_gained: isPioneer ? 50 : 25,
          is_pioneer: isPioneer,
          photo_url: null,
          already_discovered: false,
        };
        MOCK_DISCOVERED_IDS.add(pick.id);
        addDiscovery(data.plant_id, data.xp_gained, data.is_pioneer);
        setResult(data as any);
        setScanning(false);
        scanY.value = 0;
        return;
      }

      if (!cameraRef.current) return;
      const photo = await cameraRef.current.takePictureAsync({ base64: true, quality: 0.7 });
      if (!photo?.base64) throw new Error('Failed to capture photo');

      const location = await Location.getCurrentPositionAsync({}).catch(() => null);

      const { data, error } = await supabase.functions.invoke('identify-plant', {
        body: {
          photo_base64: `data:image/jpeg;base64,${photo.base64}`,
          location_lat: location?.coords.latitude ?? null,
          location_lng: location?.coords.longitude ?? null,
        },
      });

      if (error) throw error;

      if (data.needs_confirmation) {
        setConfirmSuggestions(data.suggestions);
        setScanning(false);
        scanY.value = 0;
        return;
      }

      if (data.error) {
        Alert.alert('Not recognized', 'Could not identify this plant. Try a clearer photo.');
        setScanning(false);
        scanY.value = 0;
        return;
      }

      if (!data.already_discovered) {
        addDiscovery(data.plant_id, data.xp_gained, data.is_pioneer);
      }

      setResult(data);
    } catch (err: any) {
      Alert.alert('Error', err.message ?? 'Something went wrong');
    } finally {
      setScanning(false);
      scanY.value = 0;
    }
  }

  async function handleConfirmSuggestion(suggestion: Suggestion) {
    setConfirmSuggestions(null);
    setScanning(true);
    // Re-invoke edge function with the confirmed suggestion (confidence forced to 1.0)
    // The edge function handles saving
    const { data, error } = await supabase.functions.invoke('identify-plant', {
      body: {
        photo_base64: null, // photo already taken, we pass the confirmed plant directly
        confirmed_plant: suggestion,
        location_lat: null,
        location_lng: null,
      },
    });
    setScanning(false);
    if (error || data?.error) {
      Alert.alert('Error', 'Could not save discovery');
      return;
    }
    if (!data.already_discovered) addDiscovery(data.plant_id, data.xp_gained, data.is_pioneer);
    setResult(data);
  }

  if (!permission) return <View style={styles.container} />;

  if (!permission.granted) {
    return (
      <View style={[styles.container, styles.center]}>
        <Text style={styles.permText}>Camera access needed to discover plants</Text>
        <TouchableOpacity style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Allow Camera</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.camera} facing="back">
        {/* Scan overlay frame */}
        <View style={styles.overlay}>
          <View style={styles.scanFrame}>
            <View style={[styles.corner, styles.tl]} />
            <View style={[styles.corner, styles.tr]} />
            <View style={[styles.corner, styles.bl]} />
            <View style={[styles.corner, styles.br]} />
            {scanning && (
              <Animated.View style={[styles.scanLine, scanStyle]} />
            )}
          </View>
          <Text style={styles.hint}>Point at a plant and tap to identify</Text>
        </View>
      </CameraView>

      {/* Capture button */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.captureBtn, scanning && styles.captureBtnDisabled]}
          onPress={handleCapture}
          disabled={scanning}
        >
          {scanning ? (
            <ActivityIndicator color={Colors.primary} size="large" />
          ) : (
            <View style={styles.captureInner} />
          )}
        </TouchableOpacity>
      </View>

      {/* XP Popup */}
      <XPPopup />

      {/* Confidence selection modal */}
      <Modal visible={!!confirmSuggestions} transparent animationType="slide">
        <View style={styles.modalBg}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Which plant is this?</Text>
            <Text style={styles.modalSub}>AI wasn't sure — please confirm:</Text>
            <ScrollView>
              {confirmSuggestions?.map((s, i) => (
                <TouchableOpacity
                  key={i}
                  style={styles.suggestionRow}
                  onPress={() => handleConfirmSuggestion(s)}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.suggScientific}>{s.scientific_name}</Text>
                    {s.common_name && <Text style={styles.suggCommon}>{s.common_name}</Text>}
                  </View>
                  <Text style={styles.suggConf}>{Math.round(s.confidence * 100)}%</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity
              style={styles.cancelBtn}
              onPress={() => setConfirmSuggestions(null)}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Discovery result modal */}
      <Modal visible={!!result} transparent animationType="fade">
        <View style={styles.modalBg}>
          <View style={styles.modalCard}>
            {result?.is_pioneer && (
              <Text style={styles.pioneerBanner}>⭐ FIRST DISCOVERY! +{result.xp_gained} XP</Text>
            )}
            {result && !result.is_pioneer && !result.already_discovered && (
              <Text style={styles.newDiscovery}>🌿 New Species! +{result.xp_gained} XP</Text>
            )}
            {result?.already_discovered && (
              <Text style={styles.alreadyFound}>Already in your collection</Text>
            )}
            {result?.photo_url && (
              <Image source={{ uri: result.photo_url }} style={styles.resultPhoto} />
            )}
            <Text style={styles.resultScientific}>{result?.plant.scientific_name}</Text>
            {result?.plant.common_name && (
              <Text style={styles.resultCommon}>{result.plant.common_name}</Text>
            )}
            {result?.plant.description && (
              <Text style={styles.resultDesc} numberOfLines={4}>
                {result.plant.description}
              </Text>
            )}
            <TouchableOpacity style={styles.button} onPress={() => setResult(null)}>
              <Text style={styles.buttonText}>Continue Exploring</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const CORNER_SIZE = 24;
const CORNER_THICKNESS = 3;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  center: { justifyContent: 'center', alignItems: 'center', padding: 32 },
  camera: { flex: 1 },
  overlay: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scanFrame: {
    width: 280,
    height: 280,
    position: 'relative',
    overflow: 'hidden',
  },
  corner: {
    position: 'absolute',
    width: CORNER_SIZE,
    height: CORNER_SIZE,
    borderColor: Colors.primary,
  },
  tl: { top: 0, left: 0, borderTopWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS },
  tr: { top: 0, right: 0, borderTopWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS },
  bl: { bottom: 0, left: 0, borderBottomWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS },
  br: { bottom: 0, right: 0, borderBottomWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS },
  scanLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: Colors.primary,
    opacity: 0.8,
  },
  hint: { color: Colors.text, marginTop: 16, fontSize: 13, opacity: 0.7 },
  controls: {
    height: 120,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.background,
  },
  captureBtn: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 3,
    borderColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  captureBtnDisabled: { borderColor: Colors.textDim },
  captureInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.primary,
  },
  permText: { color: Colors.text, textAlign: 'center', marginBottom: 16 },
  button: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    marginTop: 12,
  },
  buttonText: { color: Colors.background, fontWeight: '700', fontSize: 15 },
  modalBg: { flex: 1, backgroundColor: '#000000cc', justifyContent: 'flex-end' },
  modalCard: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    maxHeight: '85%',
  },
  modalTitle: { color: Colors.text, fontSize: 20, fontWeight: '700', marginBottom: 4 },
  modalSub: { color: Colors.textMuted, fontSize: 14, marginBottom: 16 },
  suggestionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 12,
    backgroundColor: Colors.card,
    marginBottom: 8,
  },
  suggScientific: { color: Colors.text, fontStyle: 'italic', fontWeight: '600' },
  suggCommon: { color: Colors.textMuted, fontSize: 13, marginTop: 2 },
  suggConf: { color: Colors.primary, fontWeight: '700', fontSize: 16 },
  cancelBtn: { padding: 14, alignItems: 'center', marginTop: 4 },
  cancelText: { color: Colors.textMuted, fontSize: 15 },
  pioneerBanner: {
    color: Colors.accent,
    fontWeight: '800',
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 8,
  },
  newDiscovery: {
    color: Colors.primary,
    fontWeight: '700',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 8,
  },
  alreadyFound: {
    color: Colors.textMuted,
    textAlign: 'center',
    marginBottom: 8,
  },
  resultPhoto: {
    width: '100%',
    height: 180,
    borderRadius: 12,
    marginBottom: 12,
  },
  resultScientific: {
    color: Colors.text,
    fontSize: 22,
    fontWeight: '700',
    fontStyle: 'italic',
    marginBottom: 4,
  },
  resultCommon: { color: Colors.primaryLight, fontSize: 16, marginBottom: 8 },
  resultDesc: { color: Colors.textMuted, fontSize: 14, lineHeight: 20 },
});
