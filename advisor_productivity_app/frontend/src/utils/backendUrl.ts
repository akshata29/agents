const FALLBACK_URL = 'http://localhost:8000'

/**
 * Resolve the backend base URL for API calls.
 * When running in the browser we default to the deployed origin if Vite did not provide a value.
 */
export const resolveBackendUrl = (): string => {
  const envUrl = import.meta.env.VITE_BACKEND_URL as string | undefined
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim()
  }

  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin
  }

  return FALLBACK_URL
}
