import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Colors } from '../constants/colors';

type Props = {
  children: React.ReactNode;
  style?: ViewStyle;
};

export function PokedexScreen({ children, style }: Props) {
  return (
    <View style={[styles.outer, style]}>
      <View style={styles.inset}>
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    backgroundColor: Colors.screenBg,
    borderWidth: 3,
    borderColor: '#2a3a2a',
    borderRadius: 4,
    marginHorizontal: 12,
    marginVertical: 6,
    overflow: 'hidden',
  },
  inset: {
    borderWidth: 1,
    borderColor: Colors.screenDim,
    opacity: 1,
  },
});
