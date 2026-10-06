import { reactive } from 'vue'
import { api } from './api'

export const authState = reactive({ loaded: false, required: false, authenticated: true })

export async function loadAuth(force = false): Promise<void> {
  if (authState.loaded && !force) return
  try {
    const status = await api.authStatus()
    authState.required = status.auth_required
    authState.authenticated = status.authenticated
  } finally {
    authState.loaded = true
  }
}
