export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_verified: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface Session {
  id: string
  device_name: string | null
  ip_address: string | null
  last_used: string
  expires_at: string
  created_at: string
}

export interface ApiError {
  detail: string
}
