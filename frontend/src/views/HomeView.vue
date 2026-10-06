<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Health } from '../api'

const health = ref<Health | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    health.value = await api.health()
  } catch (e) {
    error.value = (e as Error).message
  }
})

const label = (on: boolean) => (on ? 'configuré' : 'non configuré')
</script>

<template>
  <p>Ta ludothèque arrive bientôt.</p>
  <p v-if="error">{{ error }}</p>
  <ul v-else-if="health">
    <li>BoardGameGeek : {{ label(health.integrations.boardgamegeek) }}</li>
    <li>YouTube : {{ label(health.integrations.youtube) }}</li>
    <li>Claude : {{ label(health.integrations.claude) }}</li>
    <li>
      Sources de prix :
      {{ health.integrations.price_sources.join(', ') || 'aucune' }}
    </li>
  </ul>
</template>
