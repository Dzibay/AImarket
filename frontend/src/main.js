import { createApp } from 'vue'
import '@fontsource-variable/onest'
import '@fontsource-variable/jetbrains-mono'
import App from './App.vue'
import router from './router'
import { reveal } from './directives/reveal'
import './styles/site.css'

createApp(App).use(router).directive('reveal', reveal).mount('#app')
