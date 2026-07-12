<!--
  TileMapViewer.vue — makeTiles 瓦片地图 Vue 组件示例

  用法：
  1. 安装依赖：npm install leaflet vue
  2. 复制本文件到你的 Vue 项目 src/components/ 下
  3. 在页面中引入使用：

     <template>
       <TileMapViewer manifestUrl="http://localhost:8000/api/tiles/你的imageId/manifest" />
     </template>

     <script setup>
     import TileMapViewer from '@/components/TileMapViewer.vue'
     </script>

  Props：
  - manifestUrl (String, 必填) — makeTiles 的 manifest 地址
  - minHeight   (String, 默认 '100vh') — 地图最小高度
  - background  (String, 默认 '#1e293b') — 地图背景色
-->
<template>
  <div ref="container" class="tile-map-viewer" :style="{ minHeight, background }">
    <div ref="mapRef" class="tile-map-viewer__map"></div>
    <div v-if="loading" class="tile-map-viewer__status">加载中...</div>
    <div v-else-if="error" class="tile-map-viewer__status tile-map-viewer__status--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  manifestUrl: { type: String, required: true },
  minHeight: { type: String, default: '100vh' },
  background: { type: String, default: '#1e293b' },
})

const mapRef = ref(null)
const loading = ref(false)
const error = ref('')

let map = null

const EMPTY_TILE = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs='

function deriveBaseUrl(urlTemplate) {
  return urlTemplate.replace(/\/\{z\}\/\{x\}\/\{y\}\.\w+$/, '')
}

async function fetchJson(url) {
  const res = await fetch(url, { cache: 'no-store' })
  if (!res.ok) throw new Error(`加载失败: ${res.status}`)
  return res.json()
}

function destroyMap() {
  if (map) { map.remove(); map = null }
}

async function initMap() {
  loading.value = true
  error.value = ''
  destroyMap()

  try {
    const manifest = await fetchJson(props.manifestUrl)

    const { width, height, minZoom, maxZoom, tileSize, levels, imageExtension, urlTemplate } = manifest
    const baseUrl = deriveBaseUrl(urlTemplate)
    const ext = imageExtension || 'png'
    const tileLevels = levels || []

    map = L.map(mapRef.value, {
      crs: L.CRS.Simple,
      minZoom,
      maxZoom,
      zoomSnap: 0.25,
      zoomDelta: 0.5,
      attributionControl: false,
    })

    const sw = map.unproject([0, height], maxZoom)
    const ne = map.unproject([width, 0], maxZoom)
    const bounds = L.latLngBounds(sw, ne)
    map.setMaxBounds(bounds.pad(0.1))
    map.fitBounds(bounds)

    const TileLayer = L.GridLayer.extend({
      createTile(coords, done) {
        const tile = document.createElement('img')
        tile.width = tileSize
        tile.height = tileSize
        tile.alt = ''
        tile.draggable = false
        tile.style.width = '100%'
        tile.style.height = '100%'

        const levelInfo = tileLevels.find(l => l.z === coords.z)
        if (!levelInfo || coords.x < 0 || coords.y < 0 ||
            coords.x > levelInfo.cols - 1 || coords.y > levelInfo.rows - 1) {
          tile.src = EMPTY_TILE
          requestAnimationFrame(() => done(null, tile))
          return tile
        }

        tile.src = `${baseUrl}/${coords.z}/${coords.x}/${coords.y}.${ext}`
        tile.onload = () => done(null, tile)
        tile.onerror = () => { tile.src = EMPTY_TILE; done(null, tile) }
        return tile
      },
    })

    new TileLayer({ tileSize }).addTo(map)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(initMap)
watch(() => props.manifestUrl, initMap)
onBeforeUnmount(destroyMap)
</script>

<style scoped>
.tile-map-viewer {
  position: relative;
  width: 100%;
  overflow: hidden;
}
.tile-map-viewer__map {
  width: 100%;
  height: 100%;
  min-height: inherit;
}
.tile-map-viewer__status {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 12px 20px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  z-index: 1000;
}
.tile-map-viewer__status--error {
  color: #fca5a5;
}
:deep(.leaflet-container) {
  width: 100%;
  height: 100%;
  min-height: inherit;
  background: transparent;
}
</style>
