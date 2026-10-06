export interface Tag {
  id: number
  kind: string
  label: string
  source: string | null
}

export interface TagCount extends Tag {
  count: number
}

export interface GameSummary {
  id: number
  name_fr: string
  year: number | null
  image_url: string | null
  min_players: number | null
  max_players: number | null
  min_time: number | null
  max_time: number | null
  weight: number | null
  rating: number | null
  status: GameStatus
  base_game_id: number | null
  tags: Tag[]
}

export type GameStatus = 'owned' | 'lent' | 'wishlist' | 'sold'
export type Condition = 'new' | 'very_good' | 'good' | 'worn'
export type NoteKind = 'forgotten_rule' | 'common_mistake' | 'strategy' | 'house_rule'

export interface Note {
  id: number
  game_id: number
  kind: NoteKind
  text: string
  created_at: string
}

export interface GameFields {
  name_fr: string
  name_original: string | null
  bgg_id: number | null
  year: number | null
  publisher: string | null
  description: string | null
  image_url: string | null
  ean: string | null
  min_players: number | null
  max_players: number | null
  best_players: string | null
  min_time: number | null
  max_time: number | null
  min_age: number | null
  weight: number | null
  bgg_rating: number | null
  base_game_id: number | null
  status: GameStatus
  lent_to: string | null
  lent_since: string | null
  condition: Condition | null
  purchase_price_cents: number | null
  purchase_date: string | null
  purchase_place: string | null
  storage_location: string | null
  rating: number | null
  comment: string | null
}

export type RuleKind = 'summary' | 'beginner_guide'

export interface Video {
  id: number
  youtube_id: string
  title: string
  channel: string | null
  language: string | null
  source: 'manual' | 'auto'
  added_at: string
}

export interface VideoSuggestion {
  youtube_id: string
  title: string
  channel: string | null
  language: string | null
  duration_seconds: number | null
  priority: boolean
  already_added: boolean
}

export interface RuleSheet {
  kind: RuleKind
  content_md: string
  origin: 'manual' | 'ai_draft'
  reviewed: boolean
  updated_at: string
}

export interface RuleMeta {
  kind: RuleKind
  origin: 'manual' | 'ai_draft'
  reviewed: boolean
}

export interface GameDetail extends GameFields {
  id: number
  created_at: string
  updated_at: string
  tags: Tag[]
  notes: Note[]
  extensions: { id: number; name_fr: string }[]
  videos: Video[]
  rules: RuleMeta[]
}

export interface BggHit {
  bgg_id: number
  name: string
  year: number | null
  is_expansion: boolean
  game_id: number | null
}

export interface ImportResult {
  created: number
  skipped: number
  errors: { line: number; message: string }[]
}

export interface Status {
  integrations: {
    boardgamegeek: boolean
    youtube: boolean
    youtube_channels: string[]
    claude: boolean
    price_sources: string[]
  }
}

export interface PackEntry {
  name: string
  game_id: number | null
  game_name: string | null
  new_videos: number
  new_sheets: number
}

export interface PackPreview {
  total: number
  in_collection: number
  to_add: number
  games: PackEntry[]
}

export interface MissingGame {
  id: number
  name: string
  name_original: string | null
  year: number | null
  min_players: number | null
  max_players: number | null
  lacks: string[]
}

export interface PackResult {
  games: number
  videos_added: number
  sheets_added: number
}

export interface AuthStatus {
  auth_required: boolean
  authenticated: boolean
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
  }
}

type Params = Record<string, string | number | (string | number)[] | null | undefined>

function query(params?: Params): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === null || value === undefined || value === '') continue
    for (const item of Array.isArray(value) ? value : [value]) search.append(key, String(item))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

async function request<T>(method: string, path: string, body?: unknown, raw = false): Promise<T> {
  const headers: Record<string, string> = {}
  let payload: BodyInit | undefined
  if (raw) payload = body as string
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const response = await fetch(`/api${path}`, { method, headers, body: payload })
  if (response.status === 401 && !path.startsWith('/auth/')) {
    window.dispatchEvent(new Event('myludo:unauthorized'))
  }
  if (!response.ok) {
    let message = `Erreur ${response.status}`
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') message = data.detail
      else if (Array.isArray(data.detail)) message = 'Certaines valeurs sont invalides.'
    } catch {
      /* corps vide */
    }
    throw new ApiError(message, response.status)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export interface GameFilters {
  q?: string
  status?: GameStatus[]
  players?: number | null
  max_time?: number | null
  tag_ids?: number[]
  min_rating?: number | null
  sort?: string
}

export const api = {
  authStatus: () => request<AuthStatus>('GET', '/auth/status'),
  login: (password: string) => request<AuthStatus>('POST', '/auth/login', { password }),
  logout: () => request<AuthStatus>('POST', '/auth/logout'),
  status: () => request<Status>('GET', '/status'),

  games: (filters: GameFilters = {}) =>
    request<GameSummary[]>('GET', `/games${query(filters as Params)}`),
  game: (id: number) => request<GameDetail>('GET', `/games/${id}`),
  createGame: (fields: Partial<GameFields> & { name_fr: string }) =>
    request<GameDetail>('POST', '/games', fields),
  updateGame: (id: number, patch: Partial<GameFields>) =>
    request<GameDetail>('PATCH', `/games/${id}`, patch),
  deleteGame: (id: number) => request<void>('DELETE', `/games/${id}`),

  tags: () => request<TagCount[]>('GET', '/tags'),
  addTag: (id: number, label: string) => request<GameDetail>('POST', `/games/${id}/tags`, { label }),
  removeTag: (id: number, tagId: number) =>
    request<GameDetail>('DELETE', `/games/${id}/tags/${tagId}`),

  addNote: (id: number, kind: NoteKind, text: string) =>
    request<Note>('POST', `/games/${id}/notes`, { kind, text }),
  deleteNote: (noteId: number) => request<void>('DELETE', `/notes/${noteId}`),

  bggSearch: (q: string) => request<BggHit[]>('GET', `/bgg/search${query({ q })}`),
  bggImport: (bgg_id: number, status: GameStatus) =>
    request<GameDetail>('POST', '/bgg/import', { bgg_id, status }),

  videoSuggestions: (id: number) =>
    request<VideoSuggestion[]>('GET', `/games/${id}/videos/suggestions`),
  addVideo: (id: number, url: string, title: string) =>
    request<Video>('POST', `/games/${id}/videos`, { url, title: title || null }),
  pickVideo: (id: number, video: VideoSuggestion) =>
    request<Video>('POST', `/games/${id}/videos/pick`, {
      youtube_id: video.youtube_id,
      title: video.title,
      channel: video.channel,
      language: video.language,
    }),
  deleteVideo: (videoId: number) => request<void>('DELETE', `/videos/${videoId}`),

  rules: (id: number) => request<RuleSheet[]>('GET', `/games/${id}/rules`),
  ruleTemplates: () => request<Record<RuleKind, string>>('GET', '/rules/templates'),
  saveRule: (
    id: number,
    kind: RuleKind,
    content_md: string,
    origin: 'manual' | 'ai_draft',
    reviewed: boolean,
  ) => request<void>('PUT', `/games/${id}/rules/${kind}`, { content_md, origin, reviewed }),
  draftRule: (id: number, kind: RuleKind) =>
    request<{ content_md: string }>('POST', `/games/${id}/rules/${kind}/draft`),

  pack: () => request<PackPreview>('GET', '/pack'),
  packMissing: () => request<MissingGame[]>('GET', '/pack/missing'),
  applyPack: () => request<PackResult>('POST', '/pack/apply'),

  importCsv: (text: string) => request<ImportResult>('POST', '/import/csv', text, true),
  importJson: (text: string) => request<ImportResult>('POST', '/import/json', text, true),
}
