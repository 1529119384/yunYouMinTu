<template>
  <div class="multi-floor-viewer" :style="{ background: backgroundColor }">
    <div ref="mapRef" class="viewer-map"></div>

    <!-- 调试面板 -->
    <div class="debug-panel">
      <div>zoom: {{ debugZoom }}</div>
      <div>floor: {{ currentFloorId }}</div>
      <div>transitioning: {{ isTransitioning }}</div>
      <div>center: {{ debugCenter }}</div>
      <div>bounds: {{ debugBounds }}</div>
    </div>

    <!-- 右侧楼层切换器 -->
    <transition name="floor-panel-slide">
      <div v-if="showFloorPanel" class="floor-panel">
        <div v-for="floor in [...floors].reverse()" :key="floor.id"
             class="floor-panel__item"
             :class="{ 'floor-panel__item--active': currentFloorId === floor.id }"
             @click="switchToFloor(floor.id)">
          <span class="floor-panel__name">{{ floor.name || floor.id }}</span>
        </div>
      </div>
    </transition>

    <!-- 底部抽屉 -->
    <transition name="bottom-drawer-panel" appear>
      <div v-if="drawerVisible" class="bottom-drawer">
        <transition name="bottom-drawer-switch" mode="out-in" appear>
          <div :key="drawerKey" class="bottom-drawer__content">
            <template v-if="drawerType === 'project'">
              <div class="drawer-left">
                <h1 class="drawer-title">{{ project.title || '《项目名称》' }}</h1>
              </div>
              <div class="drawer-right">
                <p class="drawer-desc">{{ project.description }}</p>
              </div>
              <div class="drawer-hints">
                <div class="drawer-hint">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2"/>
                    <path d="M9 3v18M3 9h18"/>
                  </svg>
                  <span>按住拖动移动</span>
                </div>
                <div class="drawer-hint">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
                    <circle cx="12" cy="12" r="9"/>
                    <path d="M12 8v8M8 12h8"/>
                  </svg>
                  <span>滚轮缩放大小</span>
                </div>
              </div>
            </template>
            <template v-else-if="drawerType === 'annotation'">
              <div class="drawer-left">
                <h1 class="drawer-title">{{ activeAnnotation?.label || '标注' }}</h1>
              </div>
              <div class="drawer-right">
                <p class="drawer-desc">点击进入 {{ getFloorName(activeAnnotation?.targetFloor) }}</p>
              </div>
            </template>
            <template v-else-if="drawerType === 'marker'">
              <div class="drawer-left">
                <h1 class="drawer-title">{{ activeMarker?.title || '标点' }}</h1>
                <div class="drawer-tags">
                  <span v-for="tag in (activeMarker?.label || [])" :key="tag"
                        class="drawer-tag"
                        :style="{ backgroundColor: getTagColor(activeMarker?.color) }">
                    {{ tag }}
                  </span>
                </div>
              </div>
              <div class="drawer-right">
                <p class="drawer-desc">{{ activeMarker?.text }}</p>
              </div>
            </template>
          </div>
        </transition>
      </div>
    </transition>

    <div v-if="loading" class="viewer-overlay">正在加载切片...</div>
    <div v-else-if="error" class="viewer-overlay viewer-overlay--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { FLOOR_CONFIG } from '@/data/floors'

// ── 常量 ──────────────────────────────────────────────

const COLOR_OPTIONS = [
  { value: 'blue', tagBg: '#66cccc' },
  { value: 'blueDark', tagBg: '#1f296a' },
  { value: 'gray', tagBg: '#3b3b3b' },
  { value: 'red', tagBg: '#cc6666' },
  { value: 'orange', tagBg: '#d36839' },
  { value: 'gate', tagBg: '#1f296a' },
  { value: 'landmark', tagBg: '#1f296a' },
]

const EMPTY_TILE = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs='

// ── Props ─────────────────────────────────────────────

const props = defineProps({
  backgroundColor: { type: String, default: '#0f172a' },
})

// ── 状态 ──────────────────────────────────────────────

const mapRef = ref(null)
const loading = ref(false)
const error = ref('')

const project = ref({ title: '', description: '' })
const floors = ref([])
const currentFloorId = ref('overall')
const activeAnnotationId = ref('')
const activeMarkerId = ref('')
const isTransitioning = ref(false)

let map = null
let tileLayers = {}
let markerLayers = {}
let annotationLayers = {}
let mapMeta = null

// 调试数据
const debugZoom = ref(0)
const debugCenter = ref('')
const debugBounds = ref('')

// ── 计算属性 ──────────────────────────────────────────

const overallFloorId = computed(() => floors.value.find(f => f.id === 'overall')?.id || '')
const currentFloor = computed(() => floors.value.find(f => f.id === currentFloorId.value))
const isOverall = computed(() => currentFloorId.value === overallFloorId.value)
const showFloorPanel = computed(() => floors.value.length > 1)

const activeAnnotation = computed(() => {
  if (!currentFloor.value) return null
  return currentFloor.value.annotations?.find(a => a.id === activeAnnotationId.value)
})

const activeMarker = computed(() => {
  if (!currentFloor.value) return null
  return currentFloor.value.markers?.find(m => m.id === activeMarkerId.value)
})

const drawerType = computed(() => {
  if (activeMarker.value) return 'marker'
  if (activeAnnotation.value) return 'annotation'
  if (isOverall.value) return 'project'
  return 'none'
})

const drawerVisible = computed(() => drawerType.value !== 'none')

const drawerKey = computed(() => {
  if (activeMarker.value) return `marker-${activeMarker.value.id}-${activeMarker.value.title}`
  if (activeAnnotation.value) return `ann-${activeAnnotation.value.id}-${activeAnnotation.value.label}`
  if (isOverall.value) return `project-${project.value.title}`
  return 'empty'
})

// ── 工具函数 ──────────────────────────────────────────

function getTagColor(color) {
  return COLOR_OPTIONS.find(c => c.value === color)?.tagBg || '#66cccc'
}

function getFloorName(floorId) {
  return floors.value.find(f => f.id === floorId)?.name || floorId || '未知楼层'
}

function deriveBaseUrl(urlTemplate) {
  return urlTemplate.replace(/\/\{z\}\/\{x\}\/\{y\}\.\w+$/, '')
}

// ── Leaflet 图标 ──────────────────────────────────────

function getIconUrl(color) {
  const map = { blue: '/pin_blue.svg', blueDark: '/pin_blueDark.svg', gray: '/pin_gray.svg',
    red: '/pin_red.svg', orange: '/pin_orange.svg', gate: '/pin_gate.svg', landmark: '/pin_landmark.svg' }
  return map[color] || '/pin_blue.svg'
}

function createMarkerIcon(markerData, active = false) {
  const iconUrl = getIconUrl(markerData.color)
  const size = active ? [52, 72] : [36, 50]
  return L.icon({
    iconUrl, iconSize: size,
    iconAnchor: [size[0] / 2, size[1]],
    popupAnchor: [0, -size[1]],
  })
}

function createAnnotationIcon(active = false) {
  const size = active ? 48 : 40
  const innerR = active ? 11 : 9
  const innerFill = active ? 'rgba(102,204,204,0.9)' : 'rgba(255,255,255,0.9)'
  const outerStroke = active ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.6)'
  const html = `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="cursor:pointer">
      <circle cx="${size/2}" cy="${size/2}" r="${size/2 - 2}" fill="none" stroke="${outerStroke}" stroke-width="2.5"/>
      <circle cx="${size/2}" cy="${size/2}" r="${innerR}" fill="${innerFill}"/>
    </svg>
  `
  return L.divIcon({ html, className: 'annotation-marker', iconSize: [size, size], iconAnchor: [size/2, size/2] })
}

// ── 瓦片图层 ──────────────────────────────────────────

const ExactTileLayer = L.GridLayer.extend({
  createTile(coords, done) {
    const tile = document.createElement('img')
    const tileSize = this.getTileSize()
    const { meta, baseUrl } = this.options
    tile.width = tileSize.x; tile.height = tileSize.y
    tile.alt = ''; tile.decoding = 'async'; tile.draggable = false
    tile.style.width = `${tileSize.x}px`; tile.style.height = `${tileSize.y}px`
    tile.style.objectFit = 'fill'; tile.style.background = 'transparent'
    const ext = meta.imageExtension || 'png'
    tile.src = `${baseUrl}/${coords.z}/${coords.x}/${coords.y}.${ext}`
    tile.onload = () => done(null, tile)
    tile.onerror = () => { tile.src = EMPTY_TILE; done(null, tile) }
    return tile
  },
})

// ── 图层切换动画（PPT/Google 室内地图风格） ──────────

function waitForLayerReady(layer, timeout = 8000) {
  return new Promise(resolve => {
    if (!layer) { resolve(null); return }
    const container = layer.getContainer()
    if (!container) { resolve(null); return }

    // 主方案：监听 Leaflet GridLayer 的 load 事件
    // 该事件在所有可视瓦片完成加载/解码后触发，比 DOM 检测更可靠
    const onLoad = () => {
      layer.off('load', onLoad)
      resolve(container)
    }
    layer.once('load', onLoad)

    // 辅助检查：如果瓦片已存在且有实际解码内容，直接 resolve
    function checkLoaded() {
      const imgs = container.querySelectorAll('img.leaflet-tile')
      if (imgs.length === 0) return false
      let loaded = 0
      imgs.forEach(img => { if (img.complete && img.naturalWidth > 0) loaded++ })
      if (loaded >= Math.max(1, imgs.length * 0.3)) {
        layer.off('load', onLoad)
        resolve(container)
        return true
      }
      return false
    }

    if (checkLoaded()) return

    // 备份：MutationObserver 监测新瓦片加入 DOM
    const observer = new MutationObserver(() => {
      if (checkLoaded()) observer.disconnect()
    })
    observer.observe(container, { childList: true, subtree: true })

    // 超时兜底
    setTimeout(() => {
      observer.disconnect()
      layer.off('load', onLoad)
      resolve(container)
    }, timeout)
  })
}

function slideTransition(oldLayer, newLayer, direction = 'up', duration = 600) {
  return new Promise(resolve => {
    if (!map) { resolve(); return }

    // 旧图层未在地图上，直接淡入新图层
    if (!oldLayer || !map.hasLayer(oldLayer)) {
      if (newLayer) {
        newLayer.setOpacity(0)
        if (map.hasLayer(newLayer)) map.removeLayer(newLayer)
        newLayer.addTo(map)
        fadeInLayer(newLayer, duration).then(resolve)
      } else { resolve() }
      return
    }

    const mapEl = mapRef.value
    const isUp = direction === 'up'

    // 1. 克隆旧图层快照（瓦片已加载，可立即克隆）
    const oldContainer = oldLayer.getContainer()
    const oldTiles = oldContainer?.querySelector('.leaflet-tile-container')
    if (!oldTiles) { map.removeLayer(oldLayer); resolve(); return }

    const oldOverlay = document.createElement('div')
    oldOverlay.style.cssText = `position:absolute;inset:0;z-index:10001;overflow:hidden;pointer-events:none;background:transparent;`
    const oldCloned = oldTiles.cloneNode(true)
    oldCloned.style.position = 'absolute'
    oldCloned.style.top = '0'
    oldCloned.style.left = '0'
    oldOverlay.appendChild(oldCloned)
    mapEl.appendChild(oldOverlay)

    // 2. 添加新图层（opacity 0），移除旧图层
    if (newLayer) {
      newLayer.setOpacity(0)
      // 确保图层不在地图上，让 addTo 创建全新容器并重新请求瓦片
      if (map.hasLayer(newLayer)) map.removeLayer(newLayer)
      newLayer.addTo(map)
    }
    map.removeLayer(oldLayer)

    // 3. 等待新图层瓦片加载，然后克隆
    waitForLayerReady(newLayer).then(newContainer => {
      const newTiles = newContainer?.querySelector('.leaflet-tile-container')

      // 创建新覆盖层
      let newOverlay = null
      if (newTiles) {
        newOverlay = document.createElement('div')
        newOverlay.style.cssText = `position:absolute;inset:0;z-index:10000;overflow:hidden;pointer-events:none;background:transparent;`
        const newCloned = newTiles.cloneNode(true)
        newCloned.style.position = 'absolute'
        newCloned.style.top = '0'
        newCloned.style.left = '0'
        newOverlay.appendChild(newCloned)
        newOverlay.style.transform = isUp ? 'translateY(100%)' : 'translateY(-100%)'
        newOverlay.style.opacity = '0'
        mapEl.appendChild(newOverlay)
      }

      // 4. 预解码所有克隆图片
      const allImages = [
        ...oldCloned.querySelectorAll('img'),
        ...(newOverlay ? newOverlay.querySelectorAll('img') : []),
      ]
      const decodePromises = allImages.map(img => {
        if (img.decode) return img.decode().catch(() => {})
        return new Promise(r => { img.complete ? r() : (img.onload = r, img.onerror = r) })
      })

      Promise.all(decodePromises).then(() => {
        // 5. 强制回流后启动动画
        oldOverlay.offsetHeight
        if (newOverlay) newOverlay.offsetHeight

        const transition = `transform ${duration}ms cubic-bezier(0.22,1,0.36,1), opacity ${duration}ms ease-out`
        oldOverlay.style.transition = transition
        if (newOverlay) newOverlay.style.transition = transition

        // 旧覆盖层：滑出 + 淡出
        oldOverlay.style.transform = isUp ? 'translateY(-100%)' : 'translateY(100%)'
        oldOverlay.style.opacity = '0'

        // 新覆盖层：从屏幕外滑入 + 淡入
        if (newOverlay) {
          newOverlay.style.transform = 'translateY(0)'
          newOverlay.style.opacity = '1'
        }

        // 6. 动画结束清理
        setTimeout(() => {
          oldOverlay.remove()
          newOverlay?.remove()
          if (newLayer) newLayer.setOpacity(1)
          resolve()
        }, duration)
      })
    })
  })
}

function fadeInLayer(layer, duration = 500) {
  if (!layer || !map) return Promise.resolve()
  return new Promise(resolve => {
    if (!map.hasLayer(layer)) {
      layer.setOpacity(0)
      layer.addTo(map)
    }
    const steps = 10
    const stepTime = duration / steps
    let step = 0
    const timer = setInterval(() => {
      step++
      layer.setOpacity(step / steps)
      if (step >= steps) {
        clearInterval(timer)
        layer.setOpacity(1)
        resolve()
      }
    }, stepTime)
  })
}

// ── 标记渲染 ──────────────────────────────────────────

function renderAnnotations(floor) {
  const group = annotationLayers[floor.id]
  if (!group) return
  group.clearLayers()
  ;(floor.annotations || []).forEach(ann => {
    const latlng = L.latLng(ann.position[0], ann.position[1])
    const marker = L.marker(latlng, {
      icon: createAnnotationIcon(ann.id === activeAnnotationId.value),
      riseOnHover: true,
    })
    marker.on('click', (e) => {
      L.DomEvent.stopPropagation(e)
      handleAnnotationClick(ann)
    })
    group.addLayer(marker)
  })
}

function renderMarkers(floor) {
  const group = markerLayers[floor.id]
  if (!group) return
  group.clearLayers()
  ;(floor.markers || []).forEach(m => {
    const latlng = L.latLng(m.position[0], m.position[1])
    const marker = L.marker(latlng, {
      icon: createMarkerIcon(m, m.id === activeMarkerId.value),
      riseOnHover: true,
    })
    marker.on('click', (e) => {
      L.DomEvent.stopPropagation(e)
      handleMarkerClick(m)
    })
    group.addLayer(marker)
  })
}

function renderFloor(floor) {
  renderAnnotations(floor)
  renderMarkers(floor)
}

// ── 交互处理 ──────────────────────────────────────────

function handleAnnotationClick(ann) {
  if (isTransitioning.value) return
  activeAnnotationId.value = ann.id
  activeMarkerId.value = ''
  if (ann.targetFloor) {
    setTimeout(() => enterFloor(ann.targetFloor), 0)
  }
}

function handleMarkerClick(markerData) {
  activeMarkerId.value = markerData.id
  activeAnnotationId.value = ''
}

function handleMapBlankClick() {
  activeMarkerId.value = ''
  activeAnnotationId.value = ''
}

// ── bounds 管理 ───────────────────────────────────────

function getFloorBounds(floor) {
  const meta = floor._meta
  if (!meta) return null
  const sw = map.unproject([0, meta.height], meta.maxZoom)
  const ne = map.unproject([meta.width, 0], meta.maxZoom)
  return L.latLngBounds(sw, ne)
}

// ── 楼层切换 ──────────────────────────────────────────

async function enterFloor(floorId) {
  if (isTransitioning.value) return
  const floor = floors.value.find(f => f.id === floorId)
  if (!floor || !map) return

  isTransitioning.value = true
  activeAnnotationId.value = ''
  activeMarkerId.value = ''

  const prevFloorId = currentFloorId.value
  currentFloorId.value = floorId

  // 隐藏旧楼层 marker/annotation
  if (markerLayers[prevFloorId] && map.hasLayer(markerLayers[prevFloorId])) map.removeLayer(markerLayers[prevFloorId])
  if (annotationLayers[prevFloorId] && map.hasLayer(annotationLayers[prevFloorId])) map.removeLayer(annotationLayers[prevFloorId])

  // 确定滑动方向（根据楼层在列表中的顺序）
  const floorOrder = floors.value.map(f => f.id)
  const oldIndex = floorOrder.indexOf(prevFloorId)
  const newIndex = floorOrder.indexOf(floorId)
  const direction = newIndex >= oldIndex ? 'down' : 'up'

  const oldLayer = tileLayers[prevFloorId]
  const newLayer = tileLayers[floorId]

  await slideTransition(oldLayer, newLayer, direction)

  // zoom 限制移到动画之后，避免 Leaflet 调整视口导致画面跳动
  if (floor.viewMinZoom != null) map.setMinZoom(floor.viewMinZoom)
  if (floor.viewMaxZoom != null) map.setMaxZoom(floor.viewMaxZoom)

  // 显示新楼层 marker/annotation
  if (markerLayers[floorId]) markerLayers[floorId].addTo(map)
  if (annotationLayers[floorId]) annotationLayers[floorId].addTo(map)

  isTransitioning.value = false
}

function switchToFloor(floorId) {
  if (floorId === currentFloorId.value || isTransitioning.value) return
  enterFloor(floorId)
}

// ── 瓦片加载 ──────────────────────────────────────────

function loadFloorTiles(floor) {
  if (!floor.manifest || !map) return

  const config = floor.manifest
  floor._meta = config

  const maxZoom = Number(config.maxZoom ?? 0)
  const tileSize = Number(config.tileSize ?? 256)
  const baseUrl = deriveBaseUrl(config.urlTemplate)

  const sw = map.unproject([0, config.height], maxZoom)
  const ne = map.unproject([config.width, 0], maxZoom)
  const bounds = L.latLngBounds(sw, ne)

  const tileLayer = new ExactTileLayer({
    tileSize, minZoom: 0, maxZoom,
    noWrap: true, bounds,
    keepBuffer: 1, updateWhenIdle: true,
    meta: config, baseUrl,
  })

  tileLayers[floor.id] = tileLayer
}

// ── 初始化 ────────────────────────────────────────────

function destroyMap() {
  if (map) { map.remove(); map = null }
  tileLayers = {}; markerLayers = {}; annotationLayers = {}
  mapMeta = null
}

async function initViewer() {
  loading.value = true
  error.value = ''
  destroyMap()

  currentFloorId.value = 'overall'
  activeAnnotationId.value = ''
  activeMarkerId.value = ''
  isTransitioning.value = false

  try {
    await nextTick()
    if (!mapRef.value) throw new Error('地图容器不存在')

    project.value = FLOOR_CONFIG.project
    floors.value = FLOOR_CONFIG.floors.map(f => ({ ...f }))

    if (!floors.value.length) throw new Error('没有可加载的楼层')

    // 所有楼层共享同一个 16384×16384 坐标系
    const refConfig = floors.value[0].manifest
    if (!refConfig) throw new Error('缺少 manifest')

    mapMeta = refConfig

    const maxZoom = Number(refConfig.maxZoom ?? 5)
    const tileSize = Number(refConfig.tileSize ?? 512)

    mapRef.value.style.backgroundColor = props.backgroundColor
    const overallFloor = floors.value.find(f => f.id === 'overall')
    map = L.map(mapRef.value, {
      crs: L.CRS.Simple,
      minZoom: overallFloor?.viewMinZoom ?? 0,
      maxZoom: overallFloor?.viewMaxZoom ?? maxZoom,
      zoomControl: true, attributionControl: false,
      zoomSnap: 0.25, zoomDelta: 0.5,
      maxBoundsViscosity: 1, bounceAtZoomLimits: false, inertia: true,
    })

    // 全局 bounds（所有楼层统一 16384×16384）
    const globalSW = map.unproject([0, 16384], maxZoom)
    const globalNE = map.unproject([16384, 0], maxZoom)
    const globalBounds = L.latLngBounds(globalSW, globalNE)
    map.setMaxBounds(globalBounds.pad(0.1))

    // 加载所有楼层
    for (const floor of floors.value) {
      if (floor.manifest) loadFloorTiles(floor)
      markerLayers[floor.id] = L.layerGroup()
      annotationLayers[floor.id] = L.layerGroup()
    }

    // 初始显示整体
    currentFloorId.value = overallFloorId.value
    if (tileLayers[overallFloorId.value]) tileLayers[overallFloorId.value].addTo(map)
    markerLayers[overallFloorId.value]?.addTo(map)
    annotationLayers[overallFloorId.value]?.addTo(map)

    const overallBounds = getFloorBounds(floors.value.find(f => f.id === overallFloorId.value))
    if (overallBounds) map.fitBounds(overallBounds, { animate: false })
    map.invalidateSize(false)
    map.on('click', handleMapBlankClick)

    // 调试
    map.on('zoomend moveend', () => {
      debugZoom.value = map.getZoom().toFixed(2)
      const c = map.getCenter()
      debugCenter.value = `${c.lat.toFixed(0)}, ${c.lng.toFixed(0)}`
      const b = map.getBounds()
      debugBounds.value = `${b.getSouth().toFixed(0)},${b.getWest().toFixed(0)} - ${b.getNorth().toFixed(0)},${b.getEast().toFixed(0)}`
    })

    floors.value.forEach(f => renderFloor(f))
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(initViewer)
onBeforeUnmount(destroyMap)
</script>

<style scoped>
.multi-floor-viewer {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.viewer-map { width: 100%; height: 100%; }

.debug-panel {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: rgba(0,0,0,0.8);
  color: #0f0;
  font-family: monospace;
  font-size: 12px;
  padding: 8px 14px;
  border-radius: 6px;
  line-height: 1.6;
  pointer-events: none;
}

.floor-panel {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1000;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(8px);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.floor-panel__item {
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  text-align: center;
  white-space: nowrap;
  transition: all 0.2s;
}
.floor-panel__item:hover { background: #f1f5f9; color: #0f172a; }
.floor-panel__item--active { background: #2563eb; color: #fff; }

.floor-panel-slide-enter-active, .floor-panel-slide-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.floor-panel-slide-enter-from, .floor-panel-slide-leave-to {
  opacity: 0; transform: translateY(-50%) translateX(20px);
}

.bottom-drawer {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  height: 220px;
  overflow: hidden;
  z-index: 1000;
  pointer-events: none;
}
.bottom-drawer__content {
  height: 100%;
  box-sizing: border-box;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 -4px 24px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  padding: 24px 40px;
  pointer-events: auto;
}
.drawer-left { flex: 1; }
.drawer-right { flex: 1; text-align: right; }
.drawer-title { font-size: 26px; font-weight: 800; margin: 0 0 10px; color: #0f172a; }
.drawer-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.drawer-tag {
  display: inline-block;
  color: #fff;
  border-radius: 6px;
  padding: 5px 16px;
  font-weight: 700;
  font-size: 14px;
}
.drawer-desc { font-size: 14px; color: #475569; line-height: 1.8; max-width: 420px; margin-left: auto; }
.drawer-hints {
  flex: 1;
  display: flex;
  gap: 32px;
  justify-content: center;
  align-items: center;
}
.drawer-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.bottom-drawer-panel-enter-active, .bottom-drawer-panel-leave-active {
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.bottom-drawer-panel-enter-from, .bottom-drawer-panel-leave-to { transform: translateY(100%); }
.bottom-drawer-panel-enter-to, .bottom-drawer-panel-leave-from { transform: translateY(0); }

.bottom-drawer-switch-enter-active, .bottom-drawer-switch-leave-active {
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.2s ease;
}
.bottom-drawer-switch-enter-from, .bottom-drawer-switch-leave-to {
  opacity: 0; transform: translateY(20px);
}
.bottom-drawer-switch-enter-to, .bottom-drawer-switch-leave-from {
  opacity: 1; transform: translateY(0);
}

.viewer-overlay {
  position: absolute; inset: 0; z-index: 2000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(15,23,42,0.75); color: #e5e7eb; font-size: 16px;
}
.viewer-overlay--error { color: #fecaca; }

:deep(.leaflet-container) { width: 100%; height: 100%; background: transparent; }
:deep(.annotation-marker) { background: transparent; border: none; }

@media (max-width: 768px) {
  .floor-panel { right: 8px; }
  .floor-panel__item { padding: 6px 12px; font-size: 12px; }
  .bottom-drawer__content { padding: 16px 20px; flex-direction: column; gap: 8px; }
  .drawer-left, .drawer-right { text-align: center; }
  .drawer-desc { margin-left: 0; }
}
</style>
