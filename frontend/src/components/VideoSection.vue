<script setup lang="ts">
import { ref } from 'vue'
import { api, type Video, type VideoSuggestion } from '../api'
import { minutes } from '../labels'
import VideoPlayer from './VideoPlayer.vue'

const props = defineProps<{ gameId: number; videos: Video[] }>()
const emit = defineEmits<{ changed: [] }>()

const url = ref('')
const title = ref('')
const suggestions = ref<VideoSuggestion[] | null>(null)
const busy = ref(false)
const searching = ref(false)
const error = ref('')

async function guard(action: () => Promise<void>) {
  busy.value = true
  error.value = ''
  try {
    await action()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

const add = () =>
  guard(async () => {
    await api.addVideo(props.gameId, url.value, title.value)
    url.value = ''
    title.value = ''
    emit('changed')
  })

const remove = (video: Video) =>
  guard(async () => {
    await api.deleteVideo(video.id)
    emit('changed')
  })

async function search() {
  searching.value = true
  error.value = ''
  try {
    suggestions.value = await api.videoSuggestions(props.gameId)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    searching.value = false
  }
}

const pick = (video: VideoSuggestion) =>
  guard(async () => {
    await api.pickVideo(props.gameId, video)
    video.already_added = true
    emit('changed')
  })

const notFrench = (language: string | null) => !!language && !language.toLowerCase().startsWith('fr')
</script>

<template>
  <section class="card stack">
    <h2>Vidéos de règles</h2>
    <p v-if="!videos.length" class="muted small">
      Aucune vidéo pour l'instant. Cherche une explication en français ou colle un lien YouTube.
    </p>

    <ul v-if="videos.length" class="videos">
      <li v-for="video in videos" :key="video.id" class="stack">
        <VideoPlayer :youtube-id="video.youtube_id" :title="video.title" />
        <div class="row spread">
          <span>
            <strong>{{ video.title }}</strong>
            <span v-if="video.channel" class="muted small"> · {{ video.channel }}</span>
            <span v-if="notFrench(video.language)" class="chip">Pas en français ?</span>
          </span>
          <button class="link danger" :disabled="busy" @click="remove(video)">Retirer</button>
        </div>
      </li>
    </ul>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div class="row">
      <button :disabled="searching" @click="search">
        {{ searching ? 'Recherche…' : 'Chercher en français' }}
      </button>
    </div>

    <div v-if="suggestions">
      <p v-if="!suggestions.length" class="muted">
        Aucune vidéo française trouvée. Tu peux coller un lien ci-dessous.
      </p>
      <ul v-else class="suggestions">
        <li v-for="video in suggestions" :key="video.youtube_id" class="row spread">
          <span class="grow">
            <a :href="`https://www.youtube.com/watch?v=${video.youtube_id}`" target="_blank" rel="noopener">{{ video.title }}</a>
            <span class="muted small">
              · {{ video.channel }} <template v-if="video.duration_seconds">· {{ minutes(video.duration_seconds) }}</template>
            </span>
            <span v-if="video.priority" class="chip soft">Chaîne prioritaire</span>
          </span>
          <span v-if="video.already_added" class="muted small">Déjà ajoutée</span>
          <button v-else :disabled="busy" @click="pick(video)">Ajouter</button>
        </li>
      </ul>
      <p class="muted small">Vérifie la vidéo avant de l'ajouter : seule ta validation compte.</p>
    </div>

    <form class="stack" @submit.prevent="add">
      <div class="form-grid">
        <label class="wide">
          Lien YouTube
          <input v-model="url" type="url" placeholder="https://www.youtube.com/watch?v=…" required />
        </label>
        <label class="wide">
          Titre (facultatif)
          <input v-model="title" maxlength="300" />
        </label>
      </div>
      <button :disabled="busy || !url.trim()">Ajouter ce lien</button>
    </form>
  </section>
</template>

<style scoped>
.videos,
.suggestions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 16px;
}
.suggestions {
  gap: 10px;
}
</style>
