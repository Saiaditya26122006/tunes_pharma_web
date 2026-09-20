import { View, Text, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Stack } from 'expo-router';

import { useAuth } from '../../src/auth/AuthProvider';

export default function HomeScreen() {
  const { doctor, logout } = useAuth();

  function handleLogout() {
    Alert.alert('Log Out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: () => logout(),
      },
    ]);
  }

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <Stack.Screen options={{ title: 'Tunes Pharma' }} />

      <View style={styles.card}>
        <Text style={styles.greeting}>Welcome,</Text>
        <Text style={styles.name}>{doctor?.name ?? 'Doctor'}</Text>

        {doctor?.email ? (
          <Text style={styles.detail}>{doctor.email}</Text>
        ) : null}

        {doctor?.specialty ? (
          <Text style={styles.detail}>{doctor.specialty}</Text>
        ) : null}

        {doctor?.hospital ? (
          <Text style={styles.detail}>{doctor.hospital}</Text>
        ) : null}

        <View style={styles.badge}>
          <Text style={styles.badgeText}>Authenticated successfully</Text>
        </View>
      </View>

      <TouchableOpacity
        style={styles.logoutButton}
        onPress={handleLogout}
        testID="logout-button"
      >
        <Text style={styles.logoutText}>Log Out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  greeting: {
    fontSize: 16,
    color: '#666',
  },
  name: {
    fontSize: 24,
    fontWeight: '700',
    color: '#0A2463',
    marginTop: 4,
  },
  detail: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  badge: {
    backgroundColor: '#E8F5E9',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: 20,
    alignSelf: 'flex-start',
  },
  badgeText: {
    color: '#2E7D32',
    fontSize: 13,
    fontWeight: '600',
  },
  logoutButton: {
    marginTop: 24,
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#D32F2F',
  },
  logoutText: {
    color: '#D32F2F',
    fontSize: 16,
    fontWeight: '600',
  },
});
