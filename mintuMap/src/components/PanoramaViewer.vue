<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  sceneId: { type: String, default: 'scene1' },
  returnFloorId: { type: String, default: 'overall' },
})

const frameLoaded = ref(false)
const panoramaBaseUrl = String(
  import.meta.env.VITE_PANORAMA_BASE_URL || 'https://360.acloud.uno',
).replace(/\/$/, '')

const panoramaUrl = computed(() => {
  const url = new URL(panoramaBaseUrl, window.location.origin)
  url.searchParams.set('scene', props.sceneId)
  return url.toString()
})
</script>

<template>
  <main class="panorama-page">
    <iframe
      class="panorama-frame"
      :src="panoramaUrl"
      title="360° 全景导览"
      allow="fullscreen; gyroscope; accelerometer"
      allowfullscreen
      @load="frameLoaded = true"
    />

    <nav class="panorama-toolbar" aria-label="全景页面导航">
      <RouterLink
        class="toolbar-link"
        :to="{ name: 'floor-map', params: { floorId: returnFloorId } }"
      >
        ← 返回楼层地图
      </RouterLink>
      <span>{{ sceneId }}</span>
      <a
        class="toolbar-link"
        :href="panoramaUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        单独打开
      </a>
      <RouterLink class="toolbar-link" :to="{ name: 'floor-guide' }">
        楼层总览
      </RouterLink>
    </nav>

    <div v-if="!frameLoaded" class="panorama-loading">
      <span class="loading-ring" />
      正在进入 360° 场景…
    </div>
  </main>
</template>

<style scoped>
.panorama-page {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: #111815;
}

.panorama-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}

.panorama-toolbar {
  position: absolute;
  top: 18px;
  left: 18px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 12px;
  color: rgb(255 255 255 / 62%);
  background: rgb(15 23 20 / 76%);
  border: 1px solid rgb(255 255 255 / 12%);
  border-radius: 4px;
  font-size: 12px;
  backdrop-filter: blur(10px);
}

.toolbar-link {
  color: white;
  text-decoration: none;
}

.toolbar-link:hover,
.toolbar-link:focus-visible {
  color: #ef9a78;
  outline: none;
}

.panorama-loading {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgb(255 255 255 / 72%);
  background: #111815;
  font-size: 14px;
  pointer-events: none;
}

.loading-ring {
  width: 24px;
  height: 24px;
  border: 2px solid rgb(255 255 255 / 18%);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 600px) {
  .panorama-toolbar {
    top: 10px;
    left: 10px;
    right: 10px;
    justify-content: space-between;
  }
}
</style>
