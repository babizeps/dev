import { useEffect } from 'react';
import { Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue, useAnimatedStyle, withTiming, withSequence,
  runOnJS, Easing,
} from 'react-native-reanimated';
import { useGameStore } from '../store/gameStore';
import { Colors } from '../constants/colors';

export default function XPPopup() {
  const { pendingXpGain, clearPendingXp } = useGameStore();
  const opacity = useSharedValue(0);
  const translateY = useSharedValue(0);

  const animStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ translateY: translateY.value }],
  }));

  useEffect(() => {
    if (!pendingXpGain) return;

    opacity.value = 1;
    translateY.value = 0;

    opacity.value = withSequence(
      withTiming(1, { duration: 200 }),
      withTiming(1, { duration: 1200 }),
      withTiming(0, { duration: 400, easing: Easing.out(Easing.ease) }, (finished) => {
        if (finished) runOnJS(clearPendingXp)();
      })
    );
    translateY.value = withTiming(-80, { duration: 1800, easing: Easing.out(Easing.ease) });
  }, [pendingXpGain]);

  if (!pendingXpGain) return null;

  return (
    <Animated.View style={[styles.popup, animStyle]} pointerEvents="none">
      <Text style={styles.text}>+{pendingXpGain} XP</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  popup: {
    position: 'absolute',
    alignSelf: 'center',
    top: '40%',
    backgroundColor: Colors.accent,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
    zIndex: 999,
  },
  text: { color: '#000', fontWeight: '900', fontSize: 22 },
});
