import { createApp } from 'vue'
import '@fontsource-variable/onest'
import '@fontsource-variable/jetbrains-mono'
import App from './App.vue'
import router from './router'
import { reveal } from './directives/reveal'
import './styles/site.css'

async function boot() {
  if (import.meta.env.DEV) {
    const [{ applyDemoFlag }, { setSession }] = await Promise.all([import('./dev/demo.js'), import('./composables/useSession')])
    applyDemoFlag(setSession)
  }
  createApp(App).use(router).directive('reveal', reveal).mount('#app')
}

boot()
