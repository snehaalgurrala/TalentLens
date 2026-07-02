import { api } from "@/services/api"
import type { LoginRequest, RegisterRequest, TokenResponse, User } from "@/types"

export const authService = {
  login: (data: LoginRequest) => api.post<TokenResponse>("/auth/login", data),
  register: (data: RegisterRequest) => api.post<TokenResponse>("/auth/register", data),
  refresh: (refreshToken: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken }),
  getCurrentUser: () => api.get<User>("/users/me"),
  // No backend endpoint exists yet — kept ready for when one ships.
  // Gated behind FEATURES.forgotPasswordEnabled (see config/features.ts).
  forgotPassword: (email: string) => api.post<void>("/auth/forgot-password", { email }),
}
