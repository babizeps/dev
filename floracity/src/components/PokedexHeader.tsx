import React from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import { Colors } from '../constants/colors';

type Props = {
  title: string;
  subtitle?: string;
  rightSlot?: React.ReactNode;
};

// Pixel-art square eye indicator
function PixelEye() {
  return (
    <View style={styles.eyeOuter}>
      <View style={styles.eyeInner}>
        <View style={styles.eyeHighlight} />
      </View>
    </View>
  );
}

export function PokedexHeader({ title, subtitle, rightSlot }: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <PixelEye />

        <View style={styles.titleArea}>
          <Text style={styles.title}>▼ {title.toUpperCase()}</Text>
          {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
        </View>

        {rightSlot && <View style={styles.rightSlot}>{rightSlot}</View>}
      </View>

      {/* Pixel ridge: dark + light line */}
      <View style={styles.ridgeDark} />
      <View style={styles.ridgeLight} />
    </View>
  );
}

const mono = Platform.OS === 'ios' ? 'Courier New' : 'monospace';

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.primary,
    paddingTop: Platform.OS === 'ios' ? 52 : 16,
    paddingBottom: 0,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingBottom: 10,
    gap: 12,
  },

  // Square pixel-art eye (inset look)
  eyeOuter: {
    width: 40,
    height: 40,
    backgroundColor: '#00000044',
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: Colors.pixelShadow,
    borderLeftColor: Colors.pixelShadow,
    borderBottomColor: 'rgba(255,255,255,0.4)',
    borderRightColor: 'rgba(255,255,255,0.4)',
    padding: 3,
    justifyContent: 'center',
    alignItems: 'center',
  },
  eyeInner: {
    flex: 1,
    width: '100%',
    backgroundColor: Colors.eyeLens,
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
    padding: 3,
  },
  eyeHighlight: {
    width: 7,
    height: 7,
    backgroundColor: 'rgba(255,255,255,0.75)',
  },

  titleArea: { flex: 1 },
  title: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 1.5,
    fontFamily: mono,
  },
  subtitle: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 11,
    letterSpacing: 0.3,
    marginTop: 2,
    fontWeight: '700',
    fontFamily: mono,
  },
  rightSlot: { alignItems: 'flex-end' },
  ridgeDark: { height: 3, backgroundColor: '#00000066' },
  ridgeLight: { height: 1, backgroundColor: '#ffffff22' },
});
