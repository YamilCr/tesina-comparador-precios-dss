import { createRouter, createWebHistory } from 'vue-router'

import CompareView from '@/views/CompareView.vue'
import DataView from '@/views/DataView.vue'
import LandingView from '@/views/LandingView.vue'

export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    { path: '/comparar', name: 'compare', component: CompareView },
    { path: '/datos', name: 'data', component: DataView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
