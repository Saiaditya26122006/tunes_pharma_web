import { getApiBaseUrl, config } from '../config';
import { getAccessToken, getRefreshToken, saveTokens, clearTokens } from '../auth/tokenStorage';
import { ApiError, ApiErrorResponse, NetworkError } from './types';

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE';

interface RequestOptions {
  headers?: Record<string, string>;
  body?: unknown;
  authenticated?: boolean;
  skipRefreshRetry?: boolean;
}

let refreshPromise: Promise<boolean> | null = null;
let onAuthFailure: (() => void) | null = null;

export function setOnAuthFailure(callback: () => void): void {
  onAuthFailure = callback;
}

async function attemptTokenRefresh(): Promise<boolean> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetchWithTimeout(`${getApiBaseUrl()}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const data = await response.json();
    if (!data.success) return false;

    await saveTokens(
      data.data.tokens.access_token,
      data.data.tokens.refresh_token,
    );
    return true;
  } catch {
    return false;
  }
}

function fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.requestTimeoutMs);

  return fetch(url, { ...init, signal: controller.signal }).finally(() =>
    clearTimeout(timeout),
  );
}

async function request<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
  const { headers = {}, body, authenticated = true, skipRefreshRetry = false } = options;
  const url = `${getApiBaseUrl()}${path}`;

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  if (authenticated) {
    const token = await getAccessToken();
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  let response: Response;
  try {
    response = await fetchWithTimeout(url, {
      method,
      headers: requestHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new NetworkError('Request timed out.');
    }
    throw new NetworkError();
  }

  if (response.status === 401 && authenticated && !skipRefreshRetry) {
    if (!refreshPromise) {
      refreshPromise = attemptTokenRefresh().finally(() => {
        refreshPromise = null;
      });
    }

    const refreshed = await refreshPromise;
    if (refreshed) {
      return request<T>(method, path, { ...options, skipRefreshRetry: true });
    }

    await clearTokens();
    onAuthFailure?.();
    throw new ApiError('UNAUTHORIZED', 'Session expired. Please log in again.', 401);
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError('PARSE_ERROR', 'Invalid response from server.', response.status);
  }

  if (!response.ok) {
    const errorData = data as ApiErrorResponse;
    throw new ApiError(
      errorData?.error?.code ?? 'UNKNOWN',
      errorData?.error?.message ?? 'An unexpected error occurred.',
      response.status,
    );
  }

  const successData = data as { success: boolean; data: T; pagination?: unknown };
  return successData.data;
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'body'>) =>
    request<T>('GET', path, options),

  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'body'>) =>
    request<T>('POST', path, { ...options, body }),

  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'body'>) =>
    request<T>('PATCH', path, { ...options, body }),

  delete: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'body'>) =>
    request<T>('DELETE', path, { ...options, body }),
};
