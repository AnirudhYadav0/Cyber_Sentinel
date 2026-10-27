import { apiClient, apiRequest } from '../client'

export interface UserProfile {
  id: string
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserProfile
}

const TOKEN_KEY = 'cybersentinel_token'

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const data = await apiRequest<LoginResponse>({
      url: '/api/auth/login',
      method: 'POST',
      data: { username, password },
    })
    if (typeof window !== 'undefined' && data.access_token) {
      sessionStorage.setItem(TOKEN_KEY, data.access_token)
    }
    return data
  },

  async logout(): Promise<void> {
    try {
      await apiRequest<{ message: string }>({
        url: '/api/auth/logout',
        method: 'POST',
      })
    } finally {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(TOKEN_KEY)
      }
    }
  },

  async getMe(): Promise<UserProfile> {
    return apiRequest<UserProfile>({
      url: '/api/auth/me',
      method: 'GET',
    })
  },

  getStoredToken(): string | null {
    if (typeof window === 'undefined') return null
    return sessionStorage.getItem(TOKEN_KEY)
  },

  clearToken(): void {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem(TOKEN_KEY)
    }
  },
}
