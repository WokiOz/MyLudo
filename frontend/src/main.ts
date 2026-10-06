import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import { authState, loadAuth } from './auth'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./views/CollectionView.vue') },
    { path: '/ajouter', component: () => import('./views/AddGameView.vue') },
    { path: '/jeux/:id(\\d+)', component: () => import('./views/GameView.vue'), props: true },
    {
      path: '/jeux/:id(\\d+)/regles',
      component: () => import('./views/RulesView.vue'),
      props: true,
    },
    { path: '/reglages', component: () => import('./views/SettingsView.vue') },
    { path: '/connexion', component: () => import('./views/LoginView.vue') },
    { path: '/:rest(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  await loadAuth()
  if (authState.required && !authState.authenticated && to.path !== '/connexion') {
    return '/connexion'
  }
  if (to.path === '/connexion' && (!authState.required || authState.authenticated)) return '/'
})

window.addEventListener('myludo:unauthorized', () => {
  authState.authenticated = false
  void router.push('/connexion')
})

createApp(App).use(router).mount('#app')
