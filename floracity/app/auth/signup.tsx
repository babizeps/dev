import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, Alert,
} from 'react-native';
import { Link } from 'expo-router';
import { supabase } from '../../src/supabase/client';
import { Colors } from '../../src/constants/colors';

export default function SignupScreen() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSignup() {
    if (!username.trim()) {
      Alert.alert('Username required', 'Please choose a username.');
      return;
    }
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      setLoading(false);
      Alert.alert('Signup failed', error.message);
      return;
    }
    // Update username after profile is auto-created by trigger
    await supabase.from('profiles').update({ username }).eq('id', (await supabase.auth.getUser()).data.user!.id);
    setLoading(false);
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.inner}>
        {/* Status lights */}
        <View style={styles.statusLights}>
          <View style={[styles.light, { backgroundColor: Colors.lightRed }]} />
          <View style={[styles.light, { backgroundColor: Colors.lightYellow }]} />
          <View style={[styles.light, { backgroundColor: Colors.lightGreen }]} />
        </View>

        {/* Pokédex eye logo */}
        <View style={styles.eyeOuter}>
          <View style={styles.eyeInner}>
            <View style={styles.eyeHighlight} />
          </View>
        </View>

        <Text style={styles.title}>FloraCity</Text>
        <Text style={styles.subtitle}>Start your plant discovery journey</Text>

        <TextInput
          style={styles.input}
          placeholder="Username"
          placeholderTextColor={Colors.textMuted}
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor={Colors.textMuted}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor={Colors.textMuted}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity style={styles.button} onPress={handleSignup} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.buttonText}>CREATE ACCOUNT</Text>
          )}
        </TouchableOpacity>

        <Link href="/auth/login" asChild>
          <TouchableOpacity style={styles.link}>
            <Text style={styles.linkText}>Already have an account? Sign in →</Text>
          </TouchableOpacity>
        </Link>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  inner: { flex: 1, justifyContent: 'center', padding: 32, alignItems: 'center' },
  statusLights: { flexDirection: 'row', gap: 6, marginBottom: 24 },
  light: { width: 12, height: 12, borderRadius: 0 },
  eyeOuter: {
    width: 80,
    height: 80,
    borderRadius: 0,
    backgroundColor: '#00000044',
    padding: 6,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderTopWidth: 4,
    borderLeftWidth: 4,
    borderBottomWidth: 4,
    borderRightWidth: 4,
    borderTopColor: '#888888',
    borderLeftColor: '#888888',
    borderBottomColor: '#ffffff44',
    borderRightColor: '#ffffff44',
  },
  eyeInner: {
    width: 68,
    height: 68,
    borderRadius: 0,
    backgroundColor: Colors.eyeLens,
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
    padding: 8,
  },
  eyeHighlight: {
    width: 14,
    height: 14,
    borderRadius: 0,
    backgroundColor: 'rgba(255,255,255,0.6)',
  },
  title: {
    fontSize: 32,
    fontWeight: '800',
    color: Colors.primary,
    textAlign: 'center',
    letterSpacing: 2,
  },
  subtitle: { fontSize: 13, color: Colors.textMuted, textAlign: 'center', marginBottom: 32, marginTop: 4 },
  input: {
    backgroundColor: Colors.surface,
    color: Colors.text,
    borderRadius: 0,
    padding: 16,
    marginBottom: 8,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: '#111111',
    borderLeftColor: '#111111',
    borderBottomColor: '#444444',
    borderRightColor: '#444444',
    fontSize: 15,
    width: '100%',
    fontFamily: Platform.OS === 'ios' ? 'Courier New' : 'monospace',
  },
  button: {
    backgroundColor: Colors.primary,
    borderRadius: 0,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
    width: '100%',
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderBottomWidth: 3,
    borderRightWidth: 3,
    borderTopColor: Colors.pixelBtnHighlight,
    borderLeftColor: Colors.pixelBtnHighlight,
    borderBottomColor: Colors.pixelBtnShadow,
    borderRightColor: Colors.pixelBtnShadow,
  },
  buttonText: { color: '#ffffff', fontWeight: '700', fontSize: 15, letterSpacing: 1 },
  link: { marginTop: 20, alignItems: 'center' },
  linkText: { color: Colors.primaryLight, fontSize: 14 },
});
