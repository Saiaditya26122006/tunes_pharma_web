jest.mock('expo-secure-store', () => {
  const store: Record<string, string> = {};
  return {
    setItemAsync: jest.fn(async (key: string, value: string) => {
      store[key] = value;
    }),
    getItemAsync: jest.fn(async (key: string) => store[key] ?? null),
    deleteItemAsync: jest.fn(async (key: string) => {
      delete store[key];
    }),
    __store: store,
  };
});

import * as tokenStorage from '../auth/tokenStorage';

beforeEach(() => {
  const store = require('expo-secure-store').__store as Record<string, string>;
  for (const key of Object.keys(store)) {
    delete store[key];
  }
});

describe('tokenStorage', () => {
  it('saves and retrieves tokens', async () => {
    await tokenStorage.saveTokens('access_abc', 'refresh_xyz');
    const tokens = await tokenStorage.getTokens();
    expect(tokens).toEqual({
      accessToken: 'access_abc',
      refreshToken: 'refresh_xyz',
    });
  });

  it('returns null when no tokens stored', async () => {
    const tokens = await tokenStorage.getTokens();
    expect(tokens).toBeNull();
  });

  it('returns individual access token', async () => {
    await tokenStorage.saveTokens('access_123', 'refresh_456');
    const access = await tokenStorage.getAccessToken();
    expect(access).toBe('access_123');
  });

  it('returns individual refresh token', async () => {
    await tokenStorage.saveTokens('access_123', 'refresh_456');
    const refresh = await tokenStorage.getRefreshToken();
    expect(refresh).toBe('refresh_456');
  });

  it('clears tokens', async () => {
    await tokenStorage.saveTokens('access_123', 'refresh_456');
    await tokenStorage.clearTokens();
    const tokens = await tokenStorage.getTokens();
    expect(tokens).toBeNull();
  });

  it('returns null for access when only refresh missing', async () => {
    const SecureStore = require('expo-secure-store');
    await SecureStore.setItemAsync('auth_access_token', 'only_access');
    const tokens = await tokenStorage.getTokens();
    expect(tokens).toBeNull();
  });
});
