import { api } from './client';
import type { LoginResponse, RefreshResponse, LogoutResponse, DoctorProfile } from './types';

export function login(username: string, password: string): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', { username, password }, { authenticated: false });
}

export function refresh(refreshToken: string): Promise<RefreshResponse> {
  return api.post<RefreshResponse>('/auth/refresh', { refresh_token: refreshToken }, { authenticated: false });
}

export function logout(refreshToken?: string): Promise<LogoutResponse> {
  return api.post<LogoutResponse>('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {});
}

export function getMe(): Promise<DoctorProfile> {
  return api.get<DoctorProfile>('/auth/me');
}
