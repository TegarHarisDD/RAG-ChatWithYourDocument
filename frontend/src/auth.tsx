import { createContext, useContext, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type AuthUser } from "./api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  setupRequired: boolean;
  login: (username: string, password: string) => Promise<void>;
  setup: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const statusQuery = useQuery({
    queryKey: ["auth", "status"],
    queryFn: api.status,
    retry: false,
    staleTime: 60_000,
  });

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: api.me,
    retry: false,
    staleTime: 60_000,
  });

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      api.login(username, password),
    onSuccess: (user) => {
      queryClient.setQueryData(["me"], user);
      void queryClient.invalidateQueries();
    },
  });

  const setupMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      api.setup(username, password),
    onSuccess: (user) => {
      queryClient.setQueryData(["me"], user);
      queryClient.setQueryData(["auth", "status"], { setup_required: false });
      void queryClient.invalidateQueries();
    },
  });

  const logoutMutation = useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      queryClient.setQueryData(["me"], null);
      queryClient.setQueryData(["auth", "status"], { setup_required: false });
      queryClient.clear();
    },
  });

  const value: AuthContextValue = {
    user: meQuery.data ?? null,
    loading: meQuery.isLoading || statusQuery.isLoading,
    setupRequired: statusQuery.data?.setup_required ?? false,
    login: async (username, password) => {
      await loginMutation.mutateAsync({ username, password });
    },
    setup: async (username, password) => {
      await setupMutation.mutateAsync({ username, password });
    },
    logout: async () => {
      await logoutMutation.mutateAsync();
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
