import { createApp } from 'vue'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import App from './App.vue'
import router from './router'
import './assets/main.css'

// Тема применяется до монтирования, чтобы не было «вспышки» тёмной темы
try {
  const theme = localStorage.getItem('atlas-theme')
  if (theme) document.documentElement.dataset.theme = theme
} catch { /* localStorage недоступен */ }

const app = createApp(App)
app.use(router)
app.use(Toast, { position: 'bottom-right', timeout: 3500, maxToasts: 4, newestOnTop: true })
app.mount('#app')
