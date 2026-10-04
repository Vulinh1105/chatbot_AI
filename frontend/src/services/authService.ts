import api from "./api";
import type { User } from "../types/auth";

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export const register = async (data: RegisterRequest) => {
  const response = await api.post("/api/v1/auth/register", data);
  return response.data;
};

export const login = async (data: LoginRequest): Promise<AuthResponse> => {
  const response = await api.post("/api/v1/auth/login/json", data);
  return response.data;
};

export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get("/api/v1/users/me");
  return response.data;
};