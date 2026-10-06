<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { authState } from './auth'

const route = useRoute()
const showNav = computed(() => route.path !== '/connexion')
</script>

<template>
  <header class="bar">
    <RouterLink to="/" class="brand">🎲 MyLudo</RouterLink>
    <nav v-if="showNav && (!authState.required || authState.authenticated)" aria-label="Navigation">
      <RouterLink to="/" exact-active-class="active">Collection</RouterLink>
      <RouterLink to="/ajouter" active-class="active">Ajouter</RouterLink>
      <RouterLink to="/reglages" active-class="active">Réglages</RouterLink>
    </nav>
  </header>
  <main class="page">
    <RouterView />
  </main>
</template>

<style scoped>
.bar {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 4px 16px;
  padding: 8px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
}
.brand {
  font-weight: 700;
  font-size: 1.15rem;
  color: var(--text);
  text-decoration: none;
}
nav {
  display: flex;
  gap: 4px;
}
nav a {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 10px;
  color: var(--text);
  text-decoration: none;
}
nav a.active {
  background: var(--accent-soft);
  font-weight: 600;
}
</style>
