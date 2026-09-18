export type UserRole = 'ADMIN' | 'IT_ASSET_MANAGER' | 'MANAGER' | 'EMPLOYEE';

export interface Department {
  id: number;
  code: string;
  name: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  department_id?: number | null;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApiError {
  detail: string | { msg: string }[];
}
