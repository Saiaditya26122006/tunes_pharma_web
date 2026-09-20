jest.mock('expo-secure-store', () => {
  const store: Record<string, string> = {};
  return {
    setItemAsync: jest.fn(async (key: string, value: string) => { store[key] = value; }),
    getItemAsync: jest.fn(async (key: string) => store[key] ?? null),
    deleteItemAsync: jest.fn(async (key: string) => { delete store[key]; }),
  };
});

const mockFetch = jest.fn();
global.fetch = mockFetch;

jest.mock('../config', () => ({
  config: { apiUrl: 'http://test.local', apiPrefix: '/api/v1', requestTimeoutMs: 5000 },
  getApiBaseUrl: () => 'http://test.local/api/v1',
}));

import * as authApi from '../api/auth';
import { ApiError } from '../api/types';

function mockResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  };
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe('auth API', () => {
  describe('login', () => {
    it('returns login response on success', async () => {
      const responseBody = {
        success: true,
        data: {
          tokens: { access_token: 'a', refresh_token: 'r', expires_in: 900, token_type: 'Bearer' },
          doctor: { id: '1', name: 'Dr. Test', specialty: 'General' },
        },
      };
      mockFetch.mockResolvedValueOnce(mockResponse(200, responseBody));

      const result = await authApi.login('testuser', 'testpass');
      expect(result.tokens.access_token).toBe('a');
      expect(result.doctor.name).toBe('Dr. Test');

      const call = mockFetch.mock.calls[0];
      expect(call[0]).toBe('http://test.local/api/v1/auth/login');
      const body = JSON.parse(call[1].body);
      expect(body.username).toBe('testuser');
      expect(body.password).toBe('testpass');
    });

    it('throws ApiError on 401', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse(401, { success: false, error: { code: 'UNAUTHORIZED', message: 'Bad creds' } }),
      );

      await expect(authApi.login('u', 'p')).rejects.toThrow(ApiError);
      try {
        await authApi.login('u', 'p');
      } catch (err) {
        // second call also fails, but we already verified type above
      }
    });

    it('throws ApiError on 429 rate limit', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse(429, { success: false, error: { code: 'RATE_LIMITED', message: 'Too many' } }),
      );

      await expect(authApi.login('u', 'p')).rejects.toThrow(ApiError);
    });
  });

  describe('getMe', () => {
    it('returns doctor profile', async () => {
      const body = {
        success: true,
        data: { id: '1', name: 'Dr. Test', specialty: 'Cardiology', hospital: '', email: '', phone: '', username: 'test' },
      };
      mockFetch.mockResolvedValueOnce(mockResponse(200, body));

      const result = await authApi.getMe();
      expect(result.name).toBe('Dr. Test');
    });
  });

  describe('logout', () => {
    it('sends refresh token in body', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse(200, { success: true, data: { message: 'Logged out.' } }),
      );

      await authApi.logout('my_refresh');
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.refresh_token).toBe('my_refresh');
    });
  });

  describe('refresh', () => {
    it('returns new tokens', async () => {
      const body = {
        success: true,
        data: {
          tokens: { access_token: 'new_a', refresh_token: 'new_r', expires_in: 900, token_type: 'Bearer' },
        },
      };
      mockFetch.mockResolvedValueOnce(mockResponse(200, body));

      const result = await authApi.refresh('old_refresh');
      expect(result.tokens.access_token).toBe('new_a');
    });

    it('throws on expired refresh token', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse(401, { success: false, error: { code: 'UNAUTHORIZED', message: 'Expired' } }),
      );

      await expect(authApi.refresh('expired')).rejects.toThrow(ApiError);
    });
  });
});
