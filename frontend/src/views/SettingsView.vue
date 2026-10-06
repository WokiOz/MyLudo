<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type ImportResult, type PackPreview, type PackResult, type Status } from '../api'
import { authState } from '../auth'

const router = useRouter()
const status = ref<Status | null>(null)
const result = ref<ImportResult | null>(null)
const error = ref('')
const busy = ref(false)
const pack = ref<PackPreview | null>(null)
const packResult = ref<PackResult | null>(null)

onMounted(async () => {
  try {
    status.value = await api.status()
    pack.value = await api.pack()
  } catch (e) {
    error.value = (e as Error).message
  }
})

async function pick(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  busy.value = true
  error.value = ''
  result.value = null
  try {
    const text = await file.text()
    result.value = file.name.toLowerCase().endsWith('.json')
      ? await api.importJson(text)
      : await api.importCsv(text)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
    input.value = ''
  }
}

async function applyPack() {
  busy.value = true
  error.value = ''
  try {
    packResult.value = await api.applyPack()
    pack.value = await api.pack()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

const owned = computed(() => pack.value?.games.filter((g) => g.game_id !== null) ?? [])

async function logout() {
  await api.logout()
  authState.authenticated = false
  await router.push('/connexion')
}

const yesNo = (on: boolean) => (on ? 'Configuré' : 'Non configuré')
</script>

<template>
  <h1>Réglages</h1>
  <div class="stack">
    <section class="card stack">
      <h2>Services</h2>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <ul v-if="status" class="services">
        <li>
          BoardGameGeek
          <span :class="status.integrations.boardgamegeek ? 'ok' : 'muted'">
            {{ yesNo(status.integrations.boardgamegeek) }}
          </span>
        </li>
        <li>
          YouTube
          <span :class="status.integrations.youtube ? 'ok' : 'muted'">
            {{ yesNo(status.integrations.youtube) }}
          </span>
        </li>
        <li>
          Claude
          <span :class="status.integrations.claude ? 'ok' : 'muted'">
            {{ yesNo(status.integrations.claude) }}
          </span>
        </li>
        <li>
          Sources de prix
          <span class="muted">{{ status.integrations.price_sources.join(', ') || 'Aucune' }}</span>
        </li>
      </ul>
      <p class="muted small">
        Les clés se règlent dans les variables d'environnement de la stack Portainer. Aucune n'est
        obligatoire : les vidéos se collent sans clé, et le reste se saisit à la main.
      </p>
    </section>

    <section v-if="pack" class="card stack">
      <h2>Règles et vidéos prêtes à l'emploi</h2>
      <p>
        {{ pack.total }} jeux courants ont déjà une vidéo LudoChrono vérifiée, des règles
        simplifiées et une fiche débutants. {{ pack.in_collection }} sont dans ta ludothèque.
      </p>
      <button class="primary" :disabled="busy || !pack.to_add" @click="applyPack">
        {{ pack.to_add ? `Compléter ${pack.to_add} jeu(x)` : 'Rien à ajouter pour l’instant' }}
      </button>
      <div v-if="packResult" class="notice" role="status">
        {{ packResult.games }} jeu(x) complété(s) : {{ packResult.videos_added }} vidéo(s) et
        {{ packResult.sheets_added }} fiche(s) ajoutées.
      </div>
      <details v-if="owned.length">
        <summary>Jeux concernés dans ta ludothèque</summary>
        <ul class="packlist">
          <li v-for="entry in owned" :key="entry.name">
            <RouterLink :to="`/jeux/${entry.game_id}`">{{ entry.game_name }}</RouterLink>
            <span class="muted small">
              {{ entry.new_videos || entry.new_sheets ? 'à compléter' : 'déjà complet' }}
            </span>
          </li>
        </ul>
      </details>
      <p class="muted small">
        Les fiches arrivent comme brouillons à relire : elles sont écrites sans le livret sous les
        yeux, vérifie-les avant de t'en servir. Ce que tu as déjà écrit n'est jamais remplacé, et
        aucun jeu n'est ajouté à ta ludothèque.
      </p>
    </section>

    <section class="card stack">
      <h2>Exporter la collection</h2>
      <div class="row">
        <a class="button" href="/api/export/games.json" download>Sauvegarde complète (JSON)</a>
        <a class="button" href="/api/export/games.csv" download>Tableur (CSV)</a>
      </div>
      <p class="muted small">
        Le JSON contient aussi les notes, les tags, les vidéos et les fiches de règles : c'est celui à garder en sauvegarde.
      </p>
    </section>

    <section class="card stack">
      <h2>Importer des jeux</h2>
      <label>
        Fichier JSON ou CSV
        <input type="file" accept=".json,.csv,text/csv,application/json" :disabled="busy" @change="pick" />
      </label>
      <p class="muted small">
        Le CSV demande au minimum une colonne « nom ». Les jeux déjà présents sont ignorés.
      </p>
      <div v-if="result" class="notice" role="status">
        {{ result.created }} jeu(x) ajouté(s), {{ result.skipped }} déjà présent(s).
        <ul v-if="result.errors.length" class="errors">
          <li v-for="e in result.errors" :key="e.line">Ligne {{ e.line }} : {{ e.message }}</li>
        </ul>
      </div>
    </section>

    <section v-if="authState.required" class="card">
      <button @click="logout">Se déconnecter</button>
    </section>
  </div>
</template>

<style scoped>
.packlist {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: grid;
  gap: 4px;
}
.packlist li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.services {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.services li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.ok {
  color: var(--ok);
}
.errors {
  margin: 8px 0 0;
  padding-left: 20px;
}
</style>
