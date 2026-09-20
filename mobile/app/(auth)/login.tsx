import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { useAuth } from '../../src/auth/AuthProvider';
import { ApiError, NetworkError } from '../../src/api/types';

type LoginState = 'idle' | 'loading' | 'error' | 'success';

export default function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [state, setState] = useState<LoginState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  async function handleLogin() {
    const trimmedUsername = username.trim();
    if (!trimmedUsername || !password) {
      setState('error');
      setErrorMessage('Please enter your username and password.');
      return;
    }

    setState('loading');
    setErrorMessage('');

    try {
      await login(trimmedUsername, password);
      setState('success');
    } catch (err) {
      setState('error');
      if (err instanceof ApiError) {
        if (err.statusCode === 401) {
          setErrorMessage('Invalid username or password.');
        } else if (err.statusCode === 429) {
          setErrorMessage('Too many login attempts. Please wait a few minutes.');
        } else {
          setErrorMessage(err.message);
        }
      } else if (err instanceof NetworkError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Something went wrong. Please try again.');
      }
    }
  }

  const isLoading = state === 'loading';

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style="dark" />
      <View style={styles.inner}>
        <View style={styles.header}>
          <Text style={styles.brand}>Tunes Pharma</Text>
          <Text style={styles.subtitle}>Doctor Portal</Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.label}>Username</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your username"
            placeholderTextColor="#999"
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            autoCorrect={false}
            editable={!isLoading}
            testID="login-username"
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your password"
            placeholderTextColor="#999"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            editable={!isLoading}
            testID="login-password"
          />

          {state === 'error' && errorMessage ? (
            <Text style={styles.error} testID="login-error">
              {errorMessage}
            </Text>
          ) : null}

          <TouchableOpacity
            style={[styles.button, isLoading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={isLoading}
            testID="login-button"
          >
            {isLoading ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.buttonText}>Log In</Text>
            )}
          </TouchableOpacity>
        </View>

        <Text style={styles.footer}>
          Contact your administrator for account access.
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  brand: {
    fontSize: 28,
    fontWeight: '700',
    color: '#0A2463',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  form: {
    gap: 4,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
    marginTop: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: '#333',
    backgroundColor: '#FAFAFA',
  },
  error: {
    color: '#D32F2F',
    fontSize: 14,
    marginTop: 12,
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#0A2463',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    textAlign: 'center',
    color: '#999',
    fontSize: 12,
    marginTop: 32,
  },
});
