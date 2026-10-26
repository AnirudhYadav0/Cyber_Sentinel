import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios'

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, '') || 'http://localhost:8000'

export class ApiError extends Error {
  statusCode?: number
  detail?: string
  isNetworkError: boolean

  constructor(message: string, statusCode?: number, detail?: string, isNetworkError = false) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.detail = detail
    this.isNetworkError = isNetworkError
  }
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor to normalize error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    if (axios.isCancel(error)) {
      return Promise.reject(new ApiError('Request was cancelled', undefined, undefined, false))
    }

    if (!error.response) {
      return Promise.reject(
        new ApiError(
          error.message || 'Network error: could not connect to CyberSentinel backend.',
          undefined,
          undefined,
          true
        )
      )
    }

    const statusCode = error.response.status
    const data = error.response.data
    const detail = typeof data === 'object' && data !== null ? data.detail || data.message : undefined
    const message = detail || `Request failed with status ${statusCode}`

    return Promise.reject(new ApiError(message, statusCode, detail, false))
  }
)

export async function apiRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.request<T>(config)
  return response.data
}
