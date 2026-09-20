import { Slot } from 'expo-router';
import { AuthProvider } from '../src/auth/AuthProvider';

export default function RootLayout() {
  return (
    <AuthProvider>
      <Slot />
    </AuthProvider>
  );
}
