import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import { revealDirective } from './directives/reveal'
import { router } from './router'
import 'leaflet/dist/leaflet.css'
import './style.css'

createApp(App).directive('reveal', revealDirective).use(createPinia()).use(router).mount('#app')
