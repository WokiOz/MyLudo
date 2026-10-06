<script setup lang="ts">
import { computed } from 'vue'
import type { GameSummary } from '../api'
import { duration, players, statusLabels } from '../labels'

const props = defineProps<{ game: GameSummary }>()

const meta = computed(() =>
  [
    players(props.game.min_players, props.game.max_players),
    duration(props.game.min_time, props.game.max_time),
  ]
    .filter(Boolean)
    .join(' · '),
)
const tags = computed(() =>
  props.game.tags.filter((t) => ['difficulty', 'duration', 'style'].includes(t.kind)).slice(0, 4),
)
</script>

<template>
  <RouterLink :to="`/jeux/${game.id}`" class="card game">
    <img
      v-if="game.image_url"
      :src="game.image_url"
      alt=""
      loading="lazy"
      referrerpolicy="no-referrer"
    />
    <div v-else class="placeholder" aria-hidden="true">🎲</div>
    <div class="body">
      <strong class="name">{{ game.name_fr }}</strong>
      <span class="muted small">{{ [game.year, meta].filter(Boolean).join(' · ') }}</span>
      <span class="row">
        <span v-if="game.rating" class="chip soft">★ {{ game.rating }}/10</span>
        <span v-if="game.status !== 'owned'" class="chip">{{ statusLabels[game.status] }}</span>
        <span v-if="game.base_game_id" class="chip">Extension</span>
      </span>
      <span class="row">
        <span v-for="tag in tags" :key="tag.id" class="chip">{{ tag.label }}</span>
      </span>
    </div>
  </RouterLink>
</template>

<style scoped>
.game {
  display: flex;
  gap: 12px;
  padding: 10px;
  color: inherit;
  text-decoration: none;
}
.game:hover {
  border-color: var(--accent);
}
img,
.placeholder {
  flex: 0 0 84px;
  width: 84px;
  height: 84px;
  border-radius: 10px;
  object-fit: cover;
  background: var(--accent-soft);
}
.placeholder {
  display: grid;
  place-items: center;
  font-size: 2rem;
}
.body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.name {
  overflow-wrap: anywhere;
}
</style>
