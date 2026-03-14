import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const FAMILY_COLORS = ['#6B5B95', '#88B04B', '#F7786B', '#45B8AC', '#EFC050', '#5B5EA6'];

function familyColor(family: string): string {
  return FAMILY_COLORS[family.charCodeAt(0) % FAMILY_COLORS.length];
}

type Props = {
  label: string;
};

export function TypeBadge({ label }: Props) {
  const color = familyColor(label);
  return (
    <View style={[styles.badge, { backgroundColor: color + 'cc' }]}>
      <Text style={styles.text}>{label.toUpperCase()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 3,
    alignSelf: 'flex-start',
  },
  text: {
    color: '#ffffff',
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
});
