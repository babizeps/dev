import React from 'react';
import { Text, StyleSheet, Platform } from 'react-native';
import { Colors } from '../constants/colors';

type Props = {
  n: number;
};

export function EntryNumber({ n }: Props) {
  const formatted = `#${String(n).padStart(3, '0')}`;
  return <Text style={styles.text}>{formatted}</Text>;
}

const styles = StyleSheet.create({
  text: {
    fontFamily: Platform.OS === 'ios' ? 'Courier New' : 'monospace',
    fontSize: 11,
    color: Colors.screenText,
    fontWeight: '700',
  },
});
