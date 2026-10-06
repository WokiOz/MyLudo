<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { Condition, GameFields, GameStatus } from '../api'
import { conditionLabels, statusLabels } from '../labels'

const props = defineProps<{
  initial?: Partial<GameFields>
  submitLabel: string
  busy?: boolean
}>()
const emit = defineEmits<{ submit: [fields: Partial<GameFields> & { name_fr: string }] }>()

const text = (v: string | number | null | undefined) => (v === null || v === undefined ? '' : String(v))
const i = props.initial ?? {}
const form = reactive({
  name_fr: text(i.name_fr),
  name_original: text(i.name_original),
  year: text(i.year),
  publisher: text(i.publisher),
  min_players: text(i.min_players),
  max_players: text(i.max_players),
  min_time: text(i.min_time),
  max_time: text(i.max_time),
  min_age: text(i.min_age),
  weight: text(i.weight),
  status: (i.status ?? 'owned') as GameStatus,
  lent_to: text(i.lent_to),
  lent_since: text(i.lent_since),
  condition: (i.condition ?? '') as Condition | '',
  price: i.purchase_price_cents === null || i.purchase_price_cents === undefined
    ? ''
    : (i.purchase_price_cents / 100).toFixed(2).replace('.', ','),
  purchase_date: text(i.purchase_date),
  purchase_place: text(i.purchase_place),
  storage_location: text(i.storage_location),
  ean: text(i.ean),
  image_url: text(i.image_url),
})
const error = ref('')

const str = (v: string) => (v.trim() === '' ? null : v.trim())
const int = (v: string) => (v.trim() === '' ? null : Math.round(Number(v.replace(',', '.'))))
const dec = (v: string) => (v.trim() === '' ? null : Number(v.replace(',', '.')))

function submit() {
  const price = dec(form.price)
  if ([int(form.year), int(form.min_players), int(form.max_players), int(form.min_time),
    int(form.max_time), int(form.min_age), dec(form.weight), price].some((n) => Number.isNaN(n))) {
    error.value = 'Un des champs numériques contient une valeur invalide.'
    return
  }
  error.value = ''
  emit('submit', {
    name_fr: form.name_fr.trim(),
    name_original: str(form.name_original),
    year: int(form.year),
    publisher: str(form.publisher),
    min_players: int(form.min_players),
    max_players: int(form.max_players),
    min_time: int(form.min_time),
    max_time: int(form.max_time),
    min_age: int(form.min_age),
    weight: dec(form.weight),
    status: form.status,
    lent_to: form.status === 'lent' ? str(form.lent_to) : null,
    lent_since: form.status === 'lent' ? str(form.lent_since) : null,
    condition: form.condition || null,
    purchase_price_cents: price === null ? null : Math.round(price * 100),
    purchase_date: str(form.purchase_date),
    purchase_place: str(form.purchase_place),
    storage_location: str(form.storage_location),
    ean: str(form.ean),
    image_url: str(form.image_url),
  })
}
</script>

<template>
  <form class="stack" @submit.prevent="submit">
    <div class="form-grid">
      <label class="wide">
        Nom du jeu (en français) *
        <input v-model="form.name_fr" required maxlength="200" />
      </label>
      <label class="wide">
        Nom d'origine
        <input v-model="form.name_original" maxlength="200" />
      </label>
      <label>Année <input v-model="form.year" inputmode="numeric" /></label>
      <label>Éditeur <input v-model="form.publisher" /></label>
      <label>Joueurs min <input v-model="form.min_players" inputmode="numeric" /></label>
      <label>Joueurs max <input v-model="form.max_players" inputmode="numeric" /></label>
      <label>Durée min (min) <input v-model="form.min_time" inputmode="numeric" /></label>
      <label>Durée max (min) <input v-model="form.max_time" inputmode="numeric" /></label>
      <label>Âge min <input v-model="form.min_age" inputmode="numeric" /></label>
      <label>
        Difficulté (1 facile à 5 expert)
        <input v-model="form.weight" inputmode="decimal" placeholder="ex. 2,3" />
      </label>
    </div>

    <div class="form-grid">
      <label>
        Statut
        <select v-model="form.status">
          <option v-for="(label, value) in statusLabels" :key="value" :value="value">
            {{ label }}
          </option>
        </select>
      </label>
      <template v-if="form.status === 'lent'">
        <label>Prêté à <input v-model="form.lent_to" /></label>
        <label>Depuis le <input v-model="form.lent_since" type="date" /></label>
      </template>
      <label>
        État
        <select v-model="form.condition">
          <option value="">—</option>
          <option v-for="(label, value) in conditionLabels" :key="value" :value="value">
            {{ label }}
          </option>
        </select>
      </label>
      <label>Prix d'achat (€) <input v-model="form.price" inputmode="decimal" /></label>
      <label>Date d'achat <input v-model="form.purchase_date" type="date" /></label>
      <label>Lieu d'achat <input v-model="form.purchase_place" /></label>
      <label>Rangement <input v-model="form.storage_location" /></label>
      <label>Code-barres (EAN) <input v-model="form.ean" inputmode="numeric" /></label>
      <label class="wide">Image (adresse web) <input v-model="form.image_url" type="url" /></label>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button class="primary" :disabled="busy">{{ submitLabel }}</button>
  </form>
</template>
