import type { GameStatus, NoteKind, RuleKind } from './api'

export const statusLabels: Record<GameStatus, string> = {
  owned: 'Possédé',
  lent: 'Prêté',
  wishlist: 'Souhaité',
  sold: 'Vendu',
}

export const conditionLabels = {
  new: 'Neuf',
  very_good: 'Très bon état',
  good: 'Bon état',
  worn: 'Usé',
} as const

export const noteKinds: { value: NoteKind; label: string; hint: string }[] = [
  { value: 'forgotten_rule', label: 'Règle souvent oubliée', hint: 'Ce qu’on oublie à chaque partie' },
  { value: 'common_mistake', label: 'Erreur fréquente', hint: 'Ce que les nouveaux font de travers' },
  { value: 'strategy', label: 'Astuce de stratégie', hint: 'Un conseil pour mieux jouer' },
  { value: 'house_rule', label: 'Variante maison', hint: 'Une règle adaptée chez nous' },
]

export const tagKindLabels: Record<string, string> = {
  difficulty: 'Difficulté',
  players: 'Joueurs',
  duration: 'Durée',
  audience: 'Public',
  style: 'Style',
  mechanic: 'Mécaniques',
  custom: 'Mes tags',
}

export function players(min: number | null, max: number | null): string {
  if (!min && !max) return ''
  if (!min || !max || min === max) return `${min || max} joueur${(min || max)! > 1 ? 's' : ''}`
  return `${min}–${max} joueurs`
}

export function duration(min: number | null, max: number | null): string {
  if (!min && !max) return ''
  if (!min || !max || min === max) return `${min || max} min`
  return `${min}–${max} min`
}

export function euros(cents: number | null): string {
  if (cents === null) return ''
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(cents / 100)
}

export const ruleKinds: { value: RuleKind; label: string; hint: string }[] = [
  { value: 'summary', label: 'Règles simplifiées', hint: 'L’essentiel pour jouer en deux minutes' },
  { value: 'beginner_guide', label: 'Fiche débutants', hint: 'Pour expliquer le jeu à de nouveaux joueurs' },
]

export function minutes(seconds: number | null): string {
  if (seconds === null) return ''
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return h ? `${h} h ${String(m).padStart(2, '0')}` : `${m} min`
}
