import { Tabs } from 'expo-router';
import { Text, View } from 'react-native';
import { Colors } from '../../src/constants/colors';

function TabIcon({ emoji, focused }: { emoji: string; focused: boolean }) {
  return (
    <View style={{
      width: 36,
      height: 36,
      borderRadius: 0,
      backgroundColor: focused ? Colors.primary : '#1f0f0f',
      borderTopWidth: focused ? 0 : 2,
      borderLeftWidth: focused ? 0 : 2,
      borderBottomWidth: focused ? 0 : 2,
      borderRightWidth: focused ? 0 : 2,
      borderTopColor: '#333333',
      borderLeftColor: '#333333',
      borderBottomColor: '#111111',
      borderRightColor: '#111111',
      justifyContent: 'center',
      alignItems: 'center',
    }}>
      <Text style={{ fontSize: focused ? 18 : 15 }}>{emoji}</Text>
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0f0505',
          borderTopColor: Colors.primary,
          borderTopWidth: 3,
          paddingBottom: 10,
          paddingTop: 6,
          height: 72,
          borderRadius: 0,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textDim,
        tabBarLabelStyle: {
          fontSize: 9,
          fontWeight: '700',
          letterSpacing: 1,
          fontFamily: 'monospace',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'FLORADEX',
          tabBarIcon: ({ focused }) => <TabIcon emoji="📖" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="camera"
        options={{
          title: 'DISCOVER',
          tabBarIcon: ({ focused }) => <TabIcon emoji="📷" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="leaderboard"
        options={{
          title: 'RANKINGS',
          tabBarIcon: ({ focused }) => <TabIcon emoji="🏆" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'PROFILE',
          tabBarIcon: ({ focused }) => <TabIcon emoji="🌱" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
