export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  pagination?: Pagination;
}

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export interface DoctorSummary {
  id: string;
  name: string;
  specialty: string;
}

export interface LoginResponse {
  tokens: TokenPair;
  doctor: DoctorSummary;
}

export interface RefreshResponse {
  tokens: TokenPair;
}

export interface LogoutResponse {
  message: string;
}

export interface DoctorProfile {
  id: string;
  name: string;
  specialty: string;
  hospital: string;
  email: string;
  phone: string;
  username: string;
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string = 'Network request failed. Check your connection.') {
    super(message);
    this.name = 'NetworkError';
  }
}
