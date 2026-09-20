import Constants from 'expo-constants';

const expoExtra = Constants.expoConfig?.extra ?? {};
const API_URL: string | undefined =
  expoExtra.EXPO_PUBLIC_API_URL ??
  (typeof globalThis !== 'undefined' && 'process' in globalThis
    ? (globalThis as Record<string, unknown>)['process'] as { env?: Record<string, string> }
    : undefined
  )?.env?.EXPO_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error(
    'EXPO_PUBLIC_API_URL is not set. ' +
    'Copy .env.example to .env and configure the API URL.',
  );
}

export const config = {
  apiUrl: API_URL,
  apiPrefix: '/api/v1',
  requestTimeoutMs: 15_000,
} as const;

export function getApiBaseUrl(): string {
  return `${config.apiUrl}${config.apiPrefix}`;
}
