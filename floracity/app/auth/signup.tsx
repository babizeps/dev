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
        <Text style={styles.logo}>🌿</Text>
        <Text style={styles.title}>Join FloraCity</Text>
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
            <ActivityIndicator color={Colors.background} />
          ) : (
            <Text style={styles.buttonText}>Create Account</Text>
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
  inner: { flex: 1, justifyContent: 'center', padding: 32 },
  logo: { fontSize: 64, textAlign: 'center', marginBottom: 8 },
  title: { fontSize: 32, fontWeight: '800', color: Colors.text, textAlign: 'center' },
  subtitle: { fontSize: 14, color: Colors.textMuted, textAlign: 'center', marginBottom: 40 },
  input: {
    backgroundColor: Colors.surface,
    color: Colors.text,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    fontSize: 16,
  },
  button: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: { color: Colors.background, fontWeight: '700', fontSize: 16 },
  link: { marginTop: 20, alignItems: 'center' },
  linkText: { color: Colors.primaryLight, fontSize: 14 },
});
