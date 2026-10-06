<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type BggHit, type GameFields, type GameStatus } from '../api'
import GameForm from '../components/GameForm.vue'

const router = useRouter()
const mode = ref<'bgg' | 'manual'>('bgg')
const q = ref('')
const status = ref<GameStatus>('owned')
const hits = ref<BggHit[]>([])
const searched = ref(false)
const busy = ref(false)
const error = ref('')

async function search() {
  busy.value = true
  error.value = ''
  try {
    hits.value = await api.bggSearch(q.value.trim())
    searched.value = true
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

async function add(hit: BggHit) {
  busy.value = true
  error.value = ''
  try {
    const game = await api.bggImport(hit.bgg_id, status.value)
    await router.push(`/jeux/${game.id}`)
  } catch (e) {
    error.value = (e as Error).message
    busy.value = false
  }
}

async function create(fields: Partial<GameFields> & { name_fr: string }) {
  busy.value = true
  error.value = ''
  try {
    const game = await api.createGame(fields)
    await router.push(`/jeux/${game.id}`)
  } catch (e) {
    error.value = (e as Error).message
    busy.value = false
  }
}
</script>

<template>
  <h1>Ajouter un jeu</h1>
  <div class="tabs" role="tablist">
    <button role="tab" :class="{ on: mode === 'bgg' }" @click="mode = 'bgg'">
      Chercher sur BoardGameGeek
    </button>
    <button role="tab" :class="{ on: mode === 'manual' }" @click="mode = 'manual'">
      Saisie manuelle
    </button>
  </div>

  <div v-if="mode === 'bgg'" class="stack">
    <form class="row" @submit.prevent="search">
      <input
        v-model="q"
        class="grow"
        type="search"
        minlength="2"
        required
        placeholder="Nom du jeu, ex. Catan"
        aria-label="Nom du jeu"
      />
      <button class="primary" :disabled="busy">Chercher</button>
    </form>
    <label class="status">
      Ajouter comme
      <select v-model="status">
        <option value="owned">Jeu possédé</option>
        <option value="wishlist">Jeu souhaité</option>
      </select>
    </label>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="error" class="muted small">
      Tu peux aussi <button class="link" @click="mode = 'manual'">saisir le jeu à la main</button>.
    </p>
    <p v-if="searched && !hits.length && !error" class="muted">Aucun résultat.</p>

    <ul v-if="hits.length" class="hits">
      <li v-for="hit in hits" :key="hit.bgg_id" class="card row spread">
        <span>
          <strong>{{ hit.name }}</strong>
          <span class="muted small"> {{ hit.year ?? '' }}</span>
          <span v-if="hit.is_expansion" class="chip soft">Extension</span>
        </span>
        <RouterLink v-if="hit.game_id" :to="`/jeux/${hit.game_id}`">Déjà ajouté</RouterLink>
        <button v-else :disabled="busy" @click="add(hit)">Ajouter</button>
      </li>
    </ul>
    <p class="muted small">
      Les noms et données viennent de BoardGameGeek, souvent en anglais. Tu peux corriger le nom
      français sur la fiche.
    </p>
  </div>

  <div v-else class="card">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <GameForm submit-label="Créer la fiche" :busy="busy" @submit="create" />
  </div>
</template>

<style scoped>
.status {
  max-width: 260px;
}
.hits {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}
</style>
