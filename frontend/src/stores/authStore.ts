import { create } from "zustand";
import type { User } from "../types/auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isInitializing: boolean;

  login: (user: User, accessToken: string) => void;
  logout: () => void;
  setInitializing: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: localStorage.getItem("accessToken"),
  isAuthenticated: Boolean(localStorage.getItem("accessToken")),
  isInitializing: Boolean(localStorage.getItem("accessToken")),

  login: (user, accessToken) => {
    localStorage.setItem("accessToken", accessToken);

    set({
      user,
      accessToken,
      isAuthenticated: true,
      isInitializing: false,
    });
  },

  logout: () => {
    localStorage.removeItem("accessToken");

    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isInitializing: false,
    });
  },

  setInitializing: (value) => {
    set({
      isInitializing: value,
    });
  },
}));