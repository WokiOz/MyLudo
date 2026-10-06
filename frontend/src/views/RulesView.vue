<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type RuleKind, type RuleSheet } from '../api'
import { ruleKinds } from '../labels'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const gameId = computed(() => Number(props.id))
const kind = computed<RuleKind>(() => (route.query.fiche === 'beginner_guide' ? 'beginner_guide' : 'summary'))
const gameName = ref('')
const sheets = ref<RuleSheet[]>([])
const templates = ref<Record<RuleKind, string> | null>(null)
const claudeReady = ref(false)
const editing = ref(false)
const draft = ref('')
const draftOrigin = ref<'manual' | 'ai_draft'>('manual')
const busy = ref(false)
const generating = ref(false)
const error = ref('')
const body = ref<HTMLElement | null>(null)

const sheet = computed(() => sheets.value.find((s) => s.kind === kind.value) ?? null)
const current = computed(() => ruleKinds.find((k) => k.value === kind.value)!)
const needsReview = computed(() => !!sheet.value && sheet.value.origin === 'ai_draft' && !sheet.value.reviewed)

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

const html = computed(() =>
  DOMPurify.sanitize(marked.parse(sheet.value?.content_md ?? '', { async: false }) as string),
)

// Les cases à cocher de l'aide-mémoire sont utilisables pendant la partie.
watch(html, () => nextTick(enableChecklists), { flush: 'post' })
function enableChecklists() {
  body.value?.querySelectorAll<HTMLInputElement>('input[type=checkbox]').forEach((box) => {
    box.disabled = false
  })
}

async function load() {
  error.value = ''
  try {
    const [game, rules, tpl, status] = await Promise.all([
      api.game(gameId.value),
      api.rules(gameId.value),
      api.ruleTemplates(),
      api.status().catch(() => null),
    ])
    gameName.value = game.name_fr
    sheets.value = rules
    templates.value = tpl
    claudeReady.value = !!status?.integrations.claude
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

function edit() {
  draft.value = sheet.value?.content_md ?? ''
  draftOrigin.value = sheet.value?.origin ?? 'manual'
  editing.value = true
}

function useTemplate() {
  if (draft.value.trim() && !confirm('Remplacer le texte actuel par le modèle ?')) return
  draft.value = templates.value?.[kind.value] ?? ''
  draftOrigin.value = 'manual'
}

async function generate() {
  if (draft.value.trim() && !confirm('Remplacer le texte actuel par un brouillon généré ?')) return
  generating.value = true
  error.value = ''
  try {
    draft.value = (await api.draftRule(gameId.value, kind.value)).content_md
    draftOrigin.value = 'ai_draft'
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    generating.value = false
  }
}

const save = () =>
  run(async () => {
    await api.saveRule(gameId.value, kind.value, draft.value, draftOrigin.value, false)
    sheets.value = await api.rules(gameId.value)
    editing.value = false
  })

const markReviewed = () =>
  run(async () => {
    if (!sheet.value) return
    await api.saveRule(gameId.value, kind.value, sheet.value.content_md, 'ai_draft', true)
    sheets.value = await api.rules(gameId.value)
  })

const print = () => window.print()

function choose(next: RuleKind) {
  editing.value = false
  void router.replace({ query: { fiche: next } })
}

onMounted(load)
watch(gameId, load)
</script>

<template>
  <div class="no-print row spread">
    <RouterLink :to="`/jeux/${id}`" class="small">← {{ gameName || 'Retour à la fiche' }}</RouterLink>
  </div>
  <h1 class="print-title">{{ gameName }}</h1>

  <div class="tabs no-print" role="tablist">
    <button
      v-for="k in ruleKinds"
      :key="k.value"
      role="tab"
      :aria-selected="kind === k.value"
      :class="{ on: kind === k.value }"
      @click="choose(k.value)"
    >
      {{ k.label }}
    </button>
  </div>

  <p v-if="error" class="error" role="alert">{{ error }}</p>

  <div v-if="editing" class="card stack no-print">
    <p class="muted small">{{ current.hint }}. Écris avec tes mots : ne recopie pas le livret.</p>
    <div class="row">
      <button type="button" @click="useTemplate">Partir du modèle</button>
      <button v-if="claudeReady" type="button" :disabled="generating" @click="generate">
        {{ generating ? 'Rédaction en cours…' : 'Générer un brouillon avec Claude' }}
      </button>
    </div>
    <p v-if="draftOrigin === 'ai_draft'" class="notice">
      Brouillon généré par une IA : il peut contenir des erreurs. Relis-le avec le livret avant de
      t'en servir.
    </p>
    <textarea
      v-model="draft"
      class="editor"
      aria-label="Texte en Markdown"
      placeholder="## Titre&#10;- une liste&#10;- [ ] une case à cocher"
    ></textarea>
    <p class="muted small">Markdown : ## titre, - liste, **gras**, - [ ] case à cocher.</p>
    <div class="row">
      <button class="primary" :disabled="busy" @click="save">Enregistrer</button>
      <button :disabled="busy" @click="editing = false">Annuler</button>
    </div>
  </div>

  <template v-else>
    <div v-if="needsReview" class="notice no-print stack">
      <span>
        Ce texte est un brouillon généré par une IA et n'a pas encore été relu. Vérifie-le avec le
        livret avant de l'utiliser.
      </span>
      <button :disabled="busy" @click="markReviewed">J'ai relu cette fiche</button>
    </div>

    <article v-if="sheet" ref="body" class="card rules" v-html="html"></article>
    <div v-else class="card stack">
      <p>Aucun texte pour « {{ current.label }} » sur ce jeu.</p>
      <button class="primary" @click="edit">Rédiger cette fiche</button>
    </div>

    <div v-if="sheet" class="row no-print actions">
      <button @click="edit">Modifier</button>
      <button @click="print">Imprimer</button>
    </div>
  </template>
</template>

<style scoped>
.print-title {
  display: none;
}
.editor {
  min-height: 320px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.95rem;
}
.actions {
  margin-top: 12px;
}
.rules {
  font-size: 1.05rem;
  line-height: 1.6;
}
.rules :deep(h2) {
  margin-top: 1.4rem;
  padding-bottom: 0.25rem;
  border-bottom: 2px solid var(--accent-soft);
}
.rules :deep(h2:first-child) {
  margin-top: 0;
}
.rules :deep(ul),
.rules :deep(ol) {
  padding-left: 1.4rem;
}
.rules :deep(li) {
  margin: 0.3rem 0;
}
.rules :deep(input[type='checkbox']) {
  width: 1.2rem;
  height: 1.2rem;
  min-height: 0;
  margin-right: 0.5rem;
  vertical-align: middle;
}
.rules :deep(ul:has(input[type='checkbox'])) {
  list-style: none;
  padding-left: 0;
}
@media print {
  .print-title {
    display: block;
  }
  .rules {
    border: 0;
    padding: 0;
  }
}
</style>
