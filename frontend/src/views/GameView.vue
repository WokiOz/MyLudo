<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, type GameDetail, type GameFields, type GameStatus, type NoteKind } from '../api'
import GameForm from '../components/GameForm.vue'
import VideoSection from '../components/VideoSection.vue'
import {
  conditionLabels,
  duration,
  euros,
  noteKinds,
  players,
  ruleKinds,
  statusLabels,
  tagKindLabels,
} from '../labels'

const props = defineProps<{ id: string }>()
const router = useRouter()

const game = ref<GameDetail | null>(null)
const error = ref('')
const editing = ref(false)
const busy = ref(false)
const comment = ref('')
const newTag = ref('')
const noteKind = ref<NoteKind>('forgotten_rule')
const noteText = ref('')

const gameId = computed(() => Number(props.id))

function show(detail: GameDetail) {
  game.value = detail
  comment.value = detail.comment ?? ''
}

async function load() {
  error.value = ''
  game.value = null
  try {
    show(await api.game(gameId.value))
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function run(action: () => Promise<void>) {
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

const refresh = () => run(async () => show(await api.game(gameId.value)))

const ruleLinks = computed(() =>
  ruleKinds.map((kind) => {
    const meta = game.value?.rules.find((r) => r.kind === kind.value)
    return {
      ...kind,
      exists: !!meta,
      unreviewed: !!meta && meta.origin === 'ai_draft' && !meta.reviewed,
    }
  }),
)

const patch = (fields: Partial<GameFields>) =>
  run(async () => show(await api.updateGame(gameId.value, fields)))

const setRating = (n: number) => patch({ rating: game.value?.rating === n ? null : n })
const setStatus = (event: Event) =>
  patch({ status: (event.target as HTMLSelectElement).value as GameStatus })

function saveComment() {
  const value = comment.value.trim() || null
  if (value !== (game.value?.comment ?? null)) void patch({ comment: value })
}

async function submitForm(fields: Partial<GameFields>) {
  await run(async () => {
    show(await api.updateGame(gameId.value, fields))
    editing.value = false
  })
}

const tagGroups = computed(() => {
  const groups = new Map<string, GameDetail['tags']>()
  for (const tag of game.value?.tags ?? []) {
    groups.set(tag.kind, [...(groups.get(tag.kind) ?? []), tag])
  }
  return [...groups.entries()].map(([kind, tags]) => ({
    kind,
    label: tagKindLabels[kind] ?? kind,
    tags,
  }))
})

const addTag = () =>
  run(async () => {
    if (!newTag.value.trim()) return
    show(await api.addTag(gameId.value, newTag.value))
    newTag.value = ''
  })

const removeTag = (tagId: number) => run(async () => show(await api.removeTag(gameId.value, tagId)))

const notesByKind = computed(() =>
  noteKinds
    .map((kind) => ({ ...kind, notes: (game.value?.notes ?? []).filter((n) => n.kind === kind.value) }))
    .filter((group) => group.notes.length),
)

const addNote = () =>
  run(async () => {
    if (!noteText.value.trim()) return
    await api.addNote(gameId.value, noteKind.value, noteText.value)
    noteText.value = ''
    show(await api.game(gameId.value))
  })

const removeNote = (noteId: number) =>
  run(async () => {
    await api.deleteNote(noteId)
    show(await api.game(gameId.value))
  })

const hint = computed(() => noteKinds.find((k) => k.value === noteKind.value)?.hint ?? '')

async function remove() {
  if (!game.value || !confirm(`Supprimer « ${game.value.name_fr} » et ses notes ?`)) return
  await run(async () => {
    await api.deleteGame(gameId.value)
    await router.push('/')
  })
}

const facts = computed(() => {
  const g = game.value
  if (!g) return []
  const rows: [string, string][] = [
    ['Joueurs', players(g.min_players, g.max_players) + (g.best_players ? ` (idéal : ${g.best_players})` : '')],
    ['Durée', duration(g.min_time, g.max_time)],
    ['Âge', g.min_age ? `${g.min_age} ans et +` : ''],
    ['Difficulté', g.weight ? `${g.weight.toFixed(1)} / 5` : ''],
    ['Note BoardGameGeek', g.bgg_rating ? `${g.bgg_rating.toFixed(1)} / 10` : ''],
    ['Éditeur', g.publisher ?? ''],
    ['État', g.condition ? conditionLabels[g.condition] : ''],
    ['Prix d’achat', euros(g.purchase_price_cents)],
    ['Acheté', [g.purchase_date, g.purchase_place].filter(Boolean).join(' · ')],
    ['Rangement', g.storage_location ?? ''],
    ['Prêté à', g.status === 'lent' ? [g.lent_to, g.lent_since && `depuis le ${g.lent_since}`].filter(Boolean).join(' ') : ''],
  ]
  return rows.filter(([, value]) => value.trim())
})

onMounted(load)
watch(gameId, load)
</script>

<template>
  <RouterLink to="/" class="small">← Retour à la collection</RouterLink>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <p v-if="!game && !error" class="muted">Chargement…</p>

  <div v-if="game" class="stack">
    <section class="card head">
      <img v-if="game.image_url" :src="game.image_url" alt="" referrerpolicy="no-referrer" />
      <div class="grow stack">
        <h1>{{ game.name_fr }}</h1>
        <p v-if="game.name_original && game.name_original !== game.name_fr" class="muted small">
          {{ game.name_original }} {{ game.year ? `(${game.year})` : '' }}
        </p>
        <label class="status">
          Statut
          <select :value="game.status" :disabled="busy" @change="setStatus">
            <option v-for="(label, value) in statusLabels" :key="value" :value="value">
              {{ label }}
            </option>
          </select>
        </label>
        <div class="row">
          <button @click="editing = !editing">{{ editing ? 'Fermer' : 'Modifier la fiche' }}</button>
          <button class="danger" :disabled="busy" @click="remove">Supprimer</button>
        </div>
      </div>
    </section>

    <section v-if="editing" class="card">
      <GameForm :initial="game" submit-label="Enregistrer" :busy="busy" @submit="submitForm" />
    </section>

    <section v-else-if="facts.length" class="card">
      <dl class="facts">
        <template v-for="[label, value] in facts" :key="label">
          <dt>{{ label }}</dt>
          <dd>{{ value }}</dd>
        </template>
      </dl>
      <p v-if="game.extensions.length" class="small">
        Extensions :
        <template v-for="(ext, index) in game.extensions" :key="ext.id">
          <RouterLink :to="`/jeux/${ext.id}`">{{ ext.name_fr }}</RouterLink
          >{{ index < game.extensions.length - 1 ? ', ' : '' }}
        </template>
      </p>
    </section>

    <section class="card stack">
      <h2>Règles et fiches</h2>
      <div class="row">
        <RouterLink
          v-for="link in ruleLinks"
          :key="link.value"
          :to="{ path: `/jeux/${game.id}/regles`, query: { fiche: link.value } }"
          class="button"
          :class="{ primary: link.exists }"
        >
          {{ link.label }}
          <span v-if="!link.exists" class="muted small">à rédiger</span>
          <span v-else-if="link.unreviewed" class="small">brouillon à relire</span>
        </RouterLink>
      </div>
    </section>

    <VideoSection :game-id="game.id" :videos="game.videos" @changed="refresh" />

    <section class="card stack">
      <h2>Ma note</h2>
      <div class="row rating" role="group" aria-label="Note sur 10">
        <button
          v-for="n in 10"
          :key="n"
          class="chip"
          :class="{ on: game.rating === n }"
          :aria-pressed="game.rating === n"
          :disabled="busy"
          @click="setRating(n)"
        >
          {{ n }}
        </button>
      </div>
      <label>
        Mon commentaire
        <textarea
          v-model="comment"
          placeholder="Ce que j'en pense, avec qui y jouer…"
          @blur="saveComment"
        ></textarea>
      </label>
    </section>

    <section class="card stack">
      <h2>Aides pour les prochaines parties</h2>
      <p v-if="!notesByKind.length" class="muted small">
        Note ici les règles qu'on oublie, les erreurs des débutants, les astuces et vos variantes.
      </p>
      <div v-for="group in notesByKind" :key="group.value">
        <h3>{{ group.label }}</h3>
        <ul class="notes">
          <li v-for="note in group.notes" :key="note.id">
            <span>{{ note.text }}</span>
            <button class="link" :aria-label="`Supprimer la note : ${note.text}`" @click="removeNote(note.id)">
              ✕
            </button>
          </li>
        </ul>
      </div>
      <form class="stack" @submit.prevent="addNote">
        <div class="row">
          <label class="grow">
            Type
            <select v-model="noteKind">
              <option v-for="k in noteKinds" :key="k.value" :value="k.value">{{ k.label }}</option>
            </select>
          </label>
        </div>
        <textarea v-model="noteText" :placeholder="hint" aria-label="Texte de la note"></textarea>
        <button :disabled="busy || !noteText.trim()">Ajouter la note</button>
      </form>
    </section>

    <section class="card stack">
      <h2>Tags</h2>
      <div v-for="group in tagGroups" :key="group.kind">
        <h3>{{ group.label }}</h3>
        <div class="row">
          <span v-for="tag in group.tags" :key="tag.id" class="chip soft">
            {{ tag.label }}
            <button
              v-if="tag.source === 'user'"
              class="link"
              :aria-label="`Retirer le tag ${tag.label}`"
              @click="removeTag(tag.id)"
            >
              ✕
            </button>
          </span>
        </div>
      </div>
      <form class="row" @submit.prevent="addTag">
        <input v-model="newTag" class="grow" maxlength="40" placeholder="Nouveau tag (ex. Soirée entre amis)" aria-label="Nouveau tag" />
        <button :disabled="busy || !newTag.trim()">Ajouter</button>
      </form>
      <p class="muted small">
        Difficulté, joueurs, durée et public sont calculés depuis la fiche.
      </p>
    </section>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.head img {
  width: 140px;
  max-height: 180px;
  object-fit: cover;
  border-radius: 10px;
  align-self: flex-start;
}
.head .grow {
  min-width: 220px;
}
.status {
  max-width: 220px;
}
.facts {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 16px;
  margin: 0;
}
.facts dt {
  color: var(--muted);
}
.facts dd {
  margin: 0;
}
.notes {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.notes li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--accent-soft);
  white-space: pre-wrap;
}
.rating .chip {
  min-width: 36px;
  justify-content: center;
  min-height: 36px;
}
</style>
