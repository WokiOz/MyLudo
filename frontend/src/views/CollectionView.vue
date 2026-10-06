<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api, type GameStatus, type GameSummary, type TagCount } from '../api'
import GameCard from '../components/GameCard.vue'
import { tagKindLabels } from '../labels'

type Tab = 'collection' | 'wishlist' | 'sold'
const tabs: { id: Tab; label: string; status: GameStatus[] }[] = [
  { id: 'collection', label: 'Ma ludothèque', status: ['owned', 'lent'] },
  { id: 'wishlist', label: 'Souhaits', status: ['wishlist'] },
  { id: 'sold', label: 'Vendus', status: ['sold'] },
]

const tab = ref<Tab>('collection')
const q = ref('')
const players = ref('')
const maxTime = ref('')
const sort = ref('name')
const selected = ref<number[]>([])
const games = ref<GameSummary[]>([])
const allTags = ref<TagCount[]>([])
const loading = ref(true)
const error = ref('')

const groups = computed(() => {
  const byKind = new Map<string, TagCount[]>()
  for (const tag of allTags.value) {
    byKind.set(tag.kind, [...(byKind.get(tag.kind) ?? []), tag])
  }
  return [...byKind.entries()].map(([kind, tags]) => ({
    kind,
    label: tagKindLabels[kind] ?? kind,
    tags,
  }))
})

const activeFilters = computed(
  () => selected.value.length + (players.value ? 1 : 0) + (maxTime.value ? 1 : 0),
)

let request = 0
async function load() {
  const current = ++request
  error.value = ''
  try {
    const result = await api.games({
      q: q.value,
      status: tabs.find((t) => t.id === tab.value)?.status,
      players: players.value ? Number(players.value) : null,
      max_time: maxTime.value ? Number(maxTime.value) : null,
      tag_ids: selected.value,
      sort: sort.value,
    })
    if (current === request) games.value = result
  } catch (e) {
    if (current === request) error.value = (e as Error).message
  } finally {
    if (current === request) loading.value = false
  }
}

function toggle(id: number) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((t) => t !== id)
    : [...selected.value, id]
}

function reset() {
  q.value = ''
  players.value = ''
  maxTime.value = ''
  selected.value = []
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(q, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
watch([tab, players, maxTime, sort, selected], load)

onMounted(async () => {
  await load()
  try {
    allTags.value = await api.tags()
  } catch {
    /* les filtres par tag restent simplement absents */
  }
})
</script>

<template>
  <div class="tabs" role="tablist">
    <button
      v-for="t in tabs"
      :key="t.id"
      role="tab"
      :aria-selected="tab === t.id"
      :class="{ on: tab === t.id }"
      @click="tab = t.id"
    >
      {{ t.label }}
    </button>
  </div>

  <div class="stack">
    <div class="row">
      <input
        v-model="q"
        class="grow search"
        type="search"
        placeholder="Rechercher un jeu…"
        aria-label="Rechercher un jeu"
      />
    </div>
    <div class="row">
      <label class="field">
        Joueurs
        <select v-model="players">
          <option value="">Tous</option>
          <option v-for="n in 8" :key="n" :value="n">{{ n }}{{ n === 8 ? ' ou +' : '' }}</option>
        </select>
      </label>
      <label class="field">
        Durée
        <select v-model="maxTime">
          <option value="">Toutes</option>
          <option value="30">30 min max</option>
          <option value="60">1 h max</option>
          <option value="120">2 h max</option>
        </select>
      </label>
      <label class="field">
        Trier par
        <select v-model="sort">
          <option value="name">Nom</option>
          <option value="rating">Ma note</option>
          <option value="recent">Ajout récent</option>
          <option value="price">Prix d'achat</option>
        </select>
      </label>
    </div>

    <details v-if="groups.length" class="card filters">
      <summary>
        Filtrer par tags
        <span v-if="selected.length" class="chip on">{{ selected.length }}</span>
      </summary>
      <div v-for="group in groups" :key="group.kind" class="group">
        <h3>{{ group.label }}</h3>
        <div class="row">
          <button
            v-for="tag in group.tags"
            :key="tag.id"
            class="chip"
            :class="{ on: selected.includes(tag.id) }"
            :aria-pressed="selected.includes(tag.id)"
            @click="toggle(tag.id)"
          >
            {{ tag.label }} <span class="count">{{ tag.count }}</span>
          </button>
        </div>
      </div>
    </details>

    <div class="row spread">
      <span class="muted small" aria-live="polite">
        {{ games.length }} jeu{{ games.length > 1 ? 'x' : '' }}
      </span>
      <button v-if="activeFilters || q" class="link" @click="reset">Effacer les filtres</button>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="muted">Chargement…</p>
    <div v-else-if="!games.length" class="card">
      <template v-if="q || activeFilters">Aucun jeu ne correspond à ces critères.</template>
      <template v-else>
        Rien ici pour l'instant. <RouterLink to="/ajouter">Ajoute ton premier jeu</RouterLink>.
      </template>
    </div>
    <ul v-else class="games">
      <li v-for="game in games" :key="game.id"><GameCard :game="game" /></li>
    </ul>
  </div>
</template>

<style scoped>
.field {
  flex: 1 1 130px;
}
.filters summary {
  cursor: pointer;
  display: flex;
  gap: 8px;
  align-items: center;
  min-height: 28px;
}
.group {
  margin-top: 12px;
}
</style>
