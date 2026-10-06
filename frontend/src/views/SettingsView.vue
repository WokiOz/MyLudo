<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type ImportResult, type Status } from '../api'
import { authState } from '../auth'

const router = useRouter()
const status = ref<Status | null>(null)
const result = ref<ImportResult | null>(null)
const error = ref('')
const busy = ref(false)

onMounted(async () => {
  try {
    status.value = await api.status()
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
        Les clés se règlent dans les variables d'environnement de la stack Portainer. Sans clé,
        tout reste utilisable à la main.
      </p>
    </section>

    <section class="card stack">
      <h2>Exporter la collection</h2>
      <div class="row">
        <a class="button" href="/api/export/games.json" download>Sauvegarde complète (JSON)</a>
        <a class="button" href="/api/export/games.csv" download>Tableur (CSV)</a>
      </div>
      <p class="muted small">
        Le JSON contient aussi les notes et les tags : c'est celui à garder en sauvegarde.
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
