import { createRouter, createWebHistory } from 'vue-router'
import show from '@/views/show.vue'
import editor from '@/views/editor.vue'
import floorMap from '@/views/floor-map.vue'
import panorama from '@/views/panorama.vue'


const routes = [
  { path: '/', name: 'floor-guide', component: show },
  { path: '/map/:floorId?', name: 'floor-map', component: floorMap },
  { path: '/panorama/:sceneId', name: 'panorama', component: panorama },
  { path: '/editor', component: editor }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
