import { createRouter, createWebHistory } from 'vue-router'
import show from '@/views/show.vue'
import editor from '@/views/editor.vue'


const routes = [
  { path: '/', component: show },
  { path: '/editor', component: editor }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router