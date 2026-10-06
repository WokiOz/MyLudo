<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { authState } from '../auth'

const router = useRouter()
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await api.login(password.value)
    authState.authenticated = true
    await router.push('/')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="card stack login" @submit.prevent="submit">
    <h1>Connexion</h1>
    <label>
      Mot de passe
      <input v-model="password" type="password" autocomplete="current-password" required autofocus />
    </label>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button class="primary" :disabled="busy">Se connecter</button>
  </form>
</template>

<style scoped>
.login {
  max-width: 360px;
  margin: 48px auto;
}
</style>
