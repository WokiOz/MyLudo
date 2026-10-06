export interface Health {
  status: string
  integrations: {
    boardgamegeek: boolean
    youtube: boolean
    claude: boolean
    price_sources: string[]
  }
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`)
  if (!response.ok) throw new Error(`Erreur ${response.status} sur ${path}`)
  return response.json() as Promise<T>
}

export const api = {
  health: () => get<Health>('/health'),
}
