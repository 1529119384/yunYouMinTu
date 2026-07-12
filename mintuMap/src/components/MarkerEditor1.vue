<template>
  <div class="editor-root">
    <div ref="mapRef" class="editor-map"></div>

    <!-- 左侧面板：楼层 + 工具 -->
    <div class="sidebar">
      <div class="sidebar__section">
        <div class="sidebar__title">楼层</div>
        <div v-for="floor in floors" :key="floor.id"
             class="sidebar__item"
             :class="{ 'sidebar__item--active': currentFloorId === floor.id }"
             @click="switchFloor(floor.id)">
          {{ floor.name }}
        </div>
      </div>

      <div class="sidebar__divider"></div>

      <div class="sidebar__section">
        <div class="sidebar__title">工具</div>
        <button class="sidebar__btn" :class="{ 'sidebar__btn--active': tool === 'marker' }" @click="toggleTool('marker')">
          <span class="sidebar__icon">📍</span>
          <span>标点</span>
        </button>
        <button class="sidebar__btn" :class="{ 'sidebar__btn--active': tool === 'annotation' }" @click="toggleTool('annotation')">
          <span class="sidebar__icon">⭕</span>
          <span>标注</span>
        </button>
        <button class="sidebar__btn" @click="exportConfig">
          <span class="sidebar__icon">💾</span>
          <span>导出</span>
        </button>
        <button class="sidebar__btn sidebar__btn--danger" @click="clearAll">
          <span class="sidebar__icon">🗑️</span>
          <span>清空</span>
        </button>
      </div>
    </div>

    <!-- 右侧编辑面板 -->
    <transition name="panel-slide">
      <div v-if="showPanel" class="edit-panel">
        <div class="edit-panel__header">
          <span class="edit-panel__title">{{ panelTitle }}</span>
          <button class="edit-panel__close" @click="closePanel">✕</button>
        </div>

        <div class="edit-panel__body">
          <!-- 标点编辑 -->
          <template v-if="editingType === 'marker' && selectedMarker">
            <label class="field">
              <span class="field__label">标题</span>
              <input v-model.trim="selectedMarker.title" type="text" class="field__input" placeholder="如：服务台" />
            </label>
            <label class="field">
              <span class="field__label">颜色</span>
              <div class="color-grid">
                <div v-for="opt in COLOR_OPTIONS" :key="opt.value"
                     class="color-swatch"
                     :class="{ 'color-swatch--active': selectedMarker.color === opt.value }"
                     :style="{ '--swatch-color': opt.tagBg }"
                     :title="opt.label"
                     @click="selectedMarker.color = opt.value">
                  <img :src="opt.icon" class="color-swatch__icon" />
                </div>
              </div>
            </label>
            <label class="field">
              <span class="field__label">类型</span>
              <select v-model="selectedMarker.type" class="field__input">
                <option v-for="t in TYPE_OPTIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </label>
            <label class="field">
              <span class="field__label">标签</span>
              <div class="tag-list">
                <span v-for="(tag, i) in selectedMarker.label" :key="i" class="tag" :style="{ backgroundColor: getTagColor(selectedMarker.color) }">
                  {{ tag }}
                  <button class="tag__x" @click="selectedMarker.label.splice(i, 1)">×</button>
                </span>
              </div>
              <input v-model="tagInput" type="text" class="field__input" placeholder="输入后回车添加" @keydown.enter.prevent="addTag" />
            </label>
            <label class="field">
              <span class="field__label">描述</span>
              <textarea v-model="selectedMarker.text" rows="4" class="field__input" placeholder="支持 HTML" />
            </label>
            <div class="field__actions">
              <button class="btn btn--danger" @click="removeMarker">删除</button>
            </div>
          </template>

          <!-- 标注编辑 -->
          <template v-else-if="editingType === 'annotation' && selectedAnnotation">
            <label class="field">
              <span class="field__label">显示文字</span>
              <input v-model.trim="selectedAnnotation.label" type="text" class="field__input" placeholder="如：1F 大厅" />
            </label>
            <label class="field">
              <span class="field__label">目标楼层</span>
              <select v-model="selectedAnnotation.targetFloor" class="field__input">
                <option value="">无</option>
                <option v-for="f in floors" :key="f.id" :value="f.id">{{ f.name }}</option>
              </select>
            </label>
            <div class="field__actions">
              <button class="btn btn--danger" @click="removeAnnotation">删除</button>
            </div>
          </template>

          <!-- 默认提示 -->
          <template v-else>
            <p class="edit-panel__hint">选择左侧工具后点击地图添加</p>
          </template>
        </div>
      </div>
    </transition>

    <!-- 底部预览抽屉 -->
    <transition name="drawer">
      <div v-if="previewData" class="drawer">
        <div class="drawer__content">
          <div class="drawer__left">
            <h2 class="drawer__title">{{ previewData.title }}</h2>
            <div v-if="previewData.tags?.length" class="drawer__tags">
              <span v-for="tag in previewData.tags" :key="tag" class="drawer__tag" :style="{ backgroundColor: previewData.tagBg }">{{ tag }}</span>
            </div>
          </div>
          <div class="drawer__right">
            <p class="drawer__desc">{{ previewData.desc }}</p>
          </div>
        </div>
      </div>
    </transition>

    <!-- 状态提示 -->
    <div v-if="tool" class="tool-hint">
      点击地图放置{{ tool === 'marker' ? '标点' : '标注' }} · 按 ESC 取消
    </div>

    <div v-if="loading" class="editor-overlay">加载中...</div>
    <div v-else-if="error" class="editor-overlay editor-overlay--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// ── 常量 ──────────────────────────────────────────────

const COLOR_OPTIONS = [
  { value: 'blue',     label: '通用',   icon: '/pin_blue.svg',     tagBg: '#66cccc' },
  { value: 'blueDark', label: '重要',   icon: '/pin_blueDark.svg', tagBg: '#1f296a' },
  { value: 'gray',     label: '附属',   icon: '/pin_gray.svg',     tagBg: '#3b3b3b' },
  { value: 'red',      label: '服务',   icon: '/pin_red.svg',      tagBg: '#cc6666' },
  { value: 'orange',   label: '餐厅',   icon: '/pin_orange.svg',   tagBg: '#d36839' },
  { value: 'gate',     label: '入口',   icon: '/pin_gate.svg',     tagBg: '#1f296a' },
  { value: 'landmark', label: '地标',   icon: '/pin_landmark.svg', tagBg: '#1f296a' },
]

const TYPE_OPTIONS = [
  { value: 'building',  label: '建筑' },
  { value: 'entrance',  label: '入口' },
  { value: 'service',   label: '服务' },
  { value: 'landmark',  label: '地标' },
]

const EMPTY_TILE = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs='

// ── Props ─────────────────────────────────────────────

const props = defineProps({
  floors: { type: Array, required: true },
  backgroundColor: { type: String, default: '#0f172a' },
})

// ── 状态 ──────────────────────────────────────────────

const mapRef = ref(null)
const loading = ref(true)
const error = ref('')
const tool = ref(null)        // 'marker' | 'annotation' | null
const editingType = ref('')   // 'marker' | 'annotation'
const selectedId = ref('')
const tagInput = ref('')
const currentFloorId = ref(props.floors[0]?.id || '')
const floorData = ref(new Map()) // floorId → { markers: [], annotations: [] }

let map = null
const tileLayers = {}
const markerGroups = {}
const annotationGroups = {}

// ── 计算属性 ──────────────────────────────────────────

const currentFloorData = computed(() => floorData.value.get(currentFloorId.value) || { markers: [], annotations: [] })

const selectedMarker = computed(() => {
  if (editingType.value !== 'marker') return null
  return currentFloorData.value.markers.find(m => m.id === selectedId.value) || null
})

const selectedAnnotation = computed(() => {
  if (editingType.value !== 'annotation') return null
  return currentFloorData.value.annotations.find(a => a.id === selectedId.value) || null
})

const showPanel = computed(() => editingType.value === 'marker' || editingType.value === 'annotation')

const panelTitle = computed(() => {
  if (editingType.value === 'marker') return '编辑标点'
  if (editingType.value === 'annotation') return '编辑标注'
  return ''
})

const previewData = computed(() => {
  if (selectedMarker.value) {
    const m = selectedMarker.value
    return {
      title: m.title || '标点',
      tags: m.label,
      tagBg: getTagColor(m.color),
      desc: m.text || '',
    }
  }
  if (selectedAnnotation.value) {
    const a = selectedAnnotation.value
    return {
      title: a.label || '标注',
      tags: [],
      tagBg: '',
      desc: a.targetFloor ? `进入 ${getFloorName(a.targetFloor)}` : '',
    }
  }
  return null
})

// ── 工具函数 ──────────────────────────────────────────

function getTagColor(color) {
  return COLOR_OPTIONS.find(c => c.value === color)?.tagBg || '#66cccc'
}

function getIconUrl(color) {
  return COLOR_OPTIONS.find(c => c.value === color)?.icon || '/pin_blue.svg'
}

function getFloorName(floorId) {
  return props.floors.find(f => f.id === floorId)?.name || floorId
}

function deriveBaseUrl(urlTemplate) {
  return urlTemplate.replace(/\/\{z\}\/\{x\}\/\{y\}\.\w+$/, '')
}

// ── Leaflet 图标 ──────────────────────────────────────

function createMarkerIcon(data, active = false) {
  const size = active ? [52, 72] : [36, 50]
  return L.icon({
    iconUrl: getIconUrl(data.color),
    iconSize: size,
    iconAnchor: [size[0] / 2, size[1]],
    popupAnchor: [0, -size[1]],
  })
}

function createAnnotationIcon(active = false) {
  const s = active ? 48 : 40
  const r = active ? 11 : 9
  const fill = active ? 'rgba(102,204,204,0.9)' : 'rgba(255,255,255,0.9)'
  const stroke = active ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.6)'
  return L.divIcon({
    html: `<svg width="${s}" height="${s}" viewBox="0 0 ${s} ${s}" style="cursor:pointer">
      <circle cx="${s/2}" cy="${s/2}" r="${s/2-2}" fill="none" stroke="${stroke}" stroke-width="2.5"/>
      <circle cx="${s/2}" cy="${s/2}" r="${r}" fill="${fill}"/>
    </svg>`,
    className: 'annotation-marker',
    iconSize: [s, s],
    iconAnchor: [s/2, s/2],
  })
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
    const ext = meta.imageExtension || meta.tileFormat || 'png'
    tile.src = `${baseUrl}/${coords.z}/${coords.x}/${coords.y}.${ext}`
    tile.onload = () => done(null, tile)
    tile.onerror = () => { tile.src = EMPTY_TILE; done(null, tile) }
    return tile
  },
})

// ── 工具切换 ──────────────────────────────────────────

function toggleTool(t) {
  tool.value = tool.value === t ? null : t
  if (tool.value && map) {
    map.getContainer().style.cursor = 'crosshair'
  } else if (map) {
    map.getContainer().style.cursor = ''
  }
}

function onMapClick(e) {
  if (!tool.value) return
  if (tool.value === 'marker') addMarker(e.latlng)
  else if (tool.value === 'annotation') addAnnotation(e.latlng)
  tool.value = null
  map.getContainer().style.cursor = ''
}

function onKeyDown(e) {
  if (e.key === 'Escape') {
    tool.value = null
    if (map) map.getContainer().style.cursor = ''
  }
}

// ── 标点管理 ──────────────────────────────────────────

function addMarker(latlng) {
  const data = {
    id: `m-${Date.now()}`,
    position: [latlng.lat, latlng.lng],
    title: `标点${currentFloorData.value.markers.length + 1}`,
    color: 'blue',
    label: [],
    text: '',
    type: 'building',
  }
  currentFloorData.value.markers.push(data)
  renderMarker(data)
  selectItem(data.id, 'marker')
}

function removeMarker() {
  if (!selectedMarker.value) return
  const id = selectedMarker.value.id
  currentFloorData.value.markers = currentFloorData.value.markers.filter(m => m.id !== id)
  const group = markerGroups[currentFloorId.value]
  if (group) group.eachLayer(l => { if (l._data?.id === id) group.removeLayer(l) })
  closePanel()
}

function renderMarker(data) {
  const group = markerGroups[currentFloorId.value]
  if (!group || !map) return
  const latlng = L.latLng(data.position[0], data.position[1])
  const marker = L.marker(latlng, {
    draggable: true,
    icon: createMarkerIcon(data, data.id === selectedId.value),
    riseOnHover: true,
  }).addTo(map)
  marker.on('click', (e) => { L.DomEvent.stopPropagation(e); selectItem(data.id, 'marker') })
  marker.on('dragend', () => { data.position = [marker.getLatLng().lat, marker.getLatLng().lng] })
  marker._data = data
  group.addLayer(marker)
}

// ── 标注管理 ──────────────────────────────────────────

function addAnnotation(latlng) {
  const data = {
    id: `a-${Date.now()}`,
    position: [latlng.lat, latlng.lng],
    label: `标注${currentFloorData.value.annotations.length + 1}`,
    targetFloor: '',
  }
  currentFloorData.value.annotations.push(data)
  renderAnnotation(data)
  selectItem(data.id, 'annotation')
}

function removeAnnotation() {
  if (!selectedAnnotation.value) return
  const id = selectedAnnotation.value.id
  currentFloorData.value.annotations = currentFloorData.value.annotations.filter(a => a.id !== id)
  const group = annotationGroups[currentFloorId.value]
  if (group) group.eachLayer(l => { if (l._data?.id === id) group.removeLayer(l) })
  closePanel()
}

function renderAnnotation(data) {
  const group = annotationGroups[currentFloorId.value]
  if (!group || !map) return
  const latlng = L.latLng(data.position[0], data.position[1])
  const marker = L.marker(latlng, {
    draggable: true,
    icon: createAnnotationIcon(data.id === selectedId.value),
    riseOnHover: true,
  }).addTo(map)
  marker.on('click', (e) => { L.DomEvent.stopPropagation(e); selectItem(data.id, 'annotation') })
  marker.on('dragend', () => { data.position = [marker.getLatLng().lat, marker.getLatLng().lng] })
  marker._data = data
  group.addLayer(marker)
}

// ── 选择 ──────────────────────────────────────────────

function selectItem(id, type) {
  selectedId.value = id
  editingType.value = type
}

function closePanel() {
  selectedId.value = ''
  editingType.value = ''
}

// ── 标签 ──────────────────────────────────────────────

function addTag() {
  const tag = tagInput.value.trim()
  if (!tag || !selectedMarker.value) return
  selectedMarker.value.label.push(tag)
  tagInput.value = ''
}

// ── 楼层切换 ──────────────────────────────────────────

function switchFloor(id) {
  currentFloorId.value = id
  closePanel()
  // 隐藏所有图层，显示当前楼层
  Object.keys(tileLayers).forEach(fid => {
    if (map.hasLayer(tileLayers[fid])) map.removeLayer(tileLayers[fid])
    if (markerGroups[fid]) map.removeLayer(markerGroups[fid])
    if (annotationGroups[fid]) map.removeLayer(annotationGroups[fid])
  })
  if (tileLayers[id]) tileLayers[id].addTo(map)
  if (markerGroups[id]) markerGroups[id].addTo(map)
  if (annotationGroups[id]) annotationGroups[id].addTo(map)
}

// ── 清空 ──────────────────────────────────────────────

function clearAll() {
  const data = currentFloorData.value
  data.markers = []
  data.annotations = []
  const mg = markerGroups[currentFloorId.value]
  const ag = annotationGroups[currentFloorId.value]
  if (mg) mg.clearLayers()
  if (ag) ag.clearLayers()
  closePanel()
}

// ── 导出 ──────────────────────────────────────────────

function exportConfig() {
  const exportData = {
    floors: props.floors.map(f => {
      const data = floorData.value.get(f.id) || { markers: [], annotations: [] }
      return {
        id: f.id,
        name: f.name,
        markers: data.markers.map(m => ({
          id: m.id, position: m.position, title: m.title,
          color: m.color, label: [...m.label], text: m.text, type: m.type,
        })),
        annotations: data.annotations.map(a => ({
          id: a.id, position: a.position, label: a.label, targetFloor: a.targetFloor,
        })),
      }
    }),
  }
  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `floors_${Date.now()}.json`; a.click()
  URL.revokeObjectURL(url)
}

// ── 初始化 ────────────────────────────────────────────

async function init() {
  loading.value = true
  error.value = ''

  try {
    await nextTick()
    if (!mapRef.value) throw new Error('地图容器不存在')

    mapRef.value.style.backgroundColor = props.backgroundColor
    map = L.map(mapRef.value, {
      crs: L.CRS.Simple,
      minZoom: 0, maxZoom: 10,
      zoomControl: true, attributionControl: false,
      zoomSnap: 0.25, zoomDelta: 0.5,
      maxBoundsViscosity: 1, bounceAtZoomLimits: false, inertia: true,
    })

    // 加载所有楼层 manifest 并创建图层
    for (const floor of props.floors) {
      // 初始化数据
      floorData.value.set(floor.id, { markers: [], annotations: [] })

      // 创建图层组
      markerGroups[floor.id] = L.layerGroup()
      annotationGroups[floor.id] = L.layerGroup()

      // 加载 manifest
      try {
        const res = await fetch(floor.manifestUrl)
        if (!res.ok) continue
        const config = await res.json()

        const width = Number(config.width)
        const height = Number(config.height)
        const maxZoom = Number(config.maxZoom ?? 5)
        const tileSize = Number(config.tileSize ?? 512)
        const baseUrl = deriveBaseUrl(config.urlTemplate)

        if (!width || !height) continue

        const sw = map.unproject([0, height], maxZoom)
        const ne = map.unproject([width, 0], maxZoom)
        const bounds = L.latLngBounds(sw, ne)

        const tileLayer = new ExactTileLayer({
          tileSize, minZoom: 0, maxZoom,
          noWrap: true, bounds,
          keepBuffer: 1, updateWhenIdle: true,
          meta: config, baseUrl,
        })

        tileLayers[floor.id] = tileLayer
      } catch (e) {
        console.warn(`加载 ${floor.name} manifest 失败:`, e)
      }
    }

    // 设置全局 bounds（所有楼层 16384×16384）
    const globalSW = map.unproject([0, 16384], 5)
    const globalNE = map.unproject([16384, 0], 5)
    map.setMaxBounds(L.latLngBounds(globalSW, globalNE).pad(0.1))

    // 显示第一层楼
    if (tileLayers[currentFloorId.value]) tileLayers[currentFloorId.value].addTo(map)
    markerGroups[currentFloorId.value]?.addTo(map)
    annotationGroups[currentFloorId.value]?.addTo(map)

    const firstBounds = tileLayers[currentFloorId.value]?.options?.bounds
    if (firstBounds) map.fitBounds(firstBounds, { animate: false })

    map.invalidateSize(false)
    map.on('click', onMapClick)
    document.addEventListener('keydown', onKeyDown)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

// ── 自动保存 ──────────────────────────────────────────

watch(floorData, () => {
  const data = {}
  floorData.value.forEach((v, k) => { data[k] = v })
  localStorage.setItem('mintumap-editor-data', JSON.stringify(data))
}, { deep: true })

// ── 生命周期 ──────────────────────────────────────────

onMounted(init)
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyDown)
  if (map) { map.remove(); map = null }
})
</script>

<style scoped>
.editor-root {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: v-bind(backgroundColor);
}
.editor-map { width: 100%; height: 100%; }

/* ── 左侧边栏 ── */
.sidebar {
  position: absolute; top: 12px; left: 12px; z-index: 1000;
  width: 140px;
  background: rgba(15,23,42,0.92);
  backdrop-filter: blur(12px);
  border-radius: 10px;
  padding: 8px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}
.sidebar__section { display: flex; flex-direction: column; gap: 2px; }
.sidebar__title {
  font-size: 11px; font-weight: 600; color: #64748b;
  text-transform: uppercase; letter-spacing: 0.5px;
  padding: 4px 8px 6px;
}
.sidebar__divider {
  height: 1px; background: rgba(255,255,255,0.08);
  margin: 6px 0;
}
.sidebar__item {
  padding: 7px 10px; border-radius: 6px;
  font-size: 13px; color: #cbd5e1;
  cursor: pointer; transition: all 0.15s;
}
.sidebar__item:hover { background: rgba(255,255,255,0.08); color: #fff; }
.sidebar__item--active { background: #2563eb; color: #fff; font-weight: 500; }

.sidebar__btn {
  display: flex; align-items: center; gap: 6px;
  width: 100%; padding: 7px 10px; border: none; border-radius: 6px;
  background: transparent; color: #cbd5e1;
  font-size: 13px; cursor: pointer; transition: all 0.15s;
  text-align: left;
}
.sidebar__btn:hover { background: rgba(255,255,255,0.08); color: #fff; }
.sidebar__btn--active { background: #2563eb; color: #fff; }
.sidebar__btn--danger:hover { background: rgba(220,38,38,0.2); color: #fca5a5; }
.sidebar__icon { font-size: 14px; width: 20px; text-align: center; }

/* ── 右侧编辑面板 ── */
.edit-panel {
  position: absolute; top: 12px; right: 12px; z-index: 1000;
  width: 280px;
  background: rgba(15,23,42,0.92);
  backdrop-filter: blur(12px);
  border-radius: 10px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.3);
  overflow: hidden;
}
.edit-panel__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.edit-panel__title { font-size: 14px; font-weight: 600; color: #f1f5f9; }
.edit-panel__close {
  width: 24px; height: 24px; border: none; border-radius: 4px;
  background: transparent; color: #64748b; font-size: 14px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.edit-panel__close:hover { background: rgba(255,255,255,0.1); color: #e2e8f0; }

.edit-panel__body {
  padding: 12px 14px;
  max-height: calc(100vh - 80px);
  overflow-y: auto;
}
.edit-panel__hint { color: #64748b; font-size: 13px; margin: 0; line-height: 1.6; }

/* ── 表单 ── */
.field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.field__label { font-size: 11px; color: #94a3b8; font-weight: 500; }
.field__input {
  width: 100%; padding: 7px 10px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: #e2e8f0; font-size: 13px;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.field__input:focus { outline: none; border-color: #2563eb; }
.field__input::placeholder { color: #475569; }
textarea.field__input { resize: vertical; min-height: 60px; }
select.field__input { cursor: pointer; }

.field__actions { display: flex; justify-content: flex-end; margin-top: 4px; }

/* ── 按钮 ── */
.btn {
  padding: 6px 14px; border: none; border-radius: 6px;
  font-size: 12px; font-weight: 500; cursor: pointer;
  transition: all 0.15s;
}
.btn--danger { background: rgba(220,38,38,0.8); color: #fff; }
.btn--danger:hover { background: rgba(220,38,38,1); }

/* ── 颜色选择器 ── */
.color-grid { display: flex; gap: 4px; flex-wrap: wrap; }
.color-swatch {
  width: 36px; height: 44px;
  border: 2px solid transparent; border-radius: 6px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
  background: rgba(255,255,255,0.04);
}
.color-swatch:hover { border-color: rgba(255,255,255,0.2); }
.color-swatch--active { border-color: #2563eb; background: rgba(37,99,235,0.15); }
.color-swatch__icon { width: 22px; height: 32px; object-fit: contain; }

/* ── 标签 ── */
.tag-list { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; }
.tag {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 8px; border-radius: 10px;
  color: #fff; font-size: 11px; font-weight: 500;
}
.tag__x {
  background: none; border: none; color: inherit;
  font-size: 13px; cursor: pointer; opacity: 0.6; padding: 0;
}
.tag__x:hover { opacity: 1; }

/* ── 工具提示 ── */
.tool-hint {
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  z-index: 1000;
  padding: 8px 16px; border-radius: 8px;
  background: rgba(15,23,42,0.9);
  backdrop-filter: blur(8px);
  color: #94a3b8; font-size: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  pointer-events: none;
}

/* ── 底部抽屉 ── */
.drawer {
  position: absolute; left: 0; right: 0; bottom: 0;
  height: 180px; z-index: 1000; pointer-events: none;
  overflow: hidden;
}
.drawer__content {
  height: 100%; box-sizing: border-box;
  background: rgba(15,23,42,0.92);
  backdrop-filter: blur(12px);
  display: flex; align-items: center;
  padding: 20px 36px;
  border-top: 1px solid rgba(255,255,255,0.06);
  pointer-events: auto;
}
.drawer__left { flex: 1; }
.drawer__right { flex: 1; text-align: right; }
.drawer__title { font-size: 24px; font-weight: 700; margin: 0 0 8px; color: #f1f5f9; }
.drawer__tags { display: flex; gap: 6px; flex-wrap: wrap; }
.drawer__tag {
  display: inline-block; color: #fff; border-radius: 6px;
  padding: 3px 12px; font-weight: 600; font-size: 13px;
}
.drawer__desc { font-size: 13px; color: #94a3b8; line-height: 1.7; max-width: 400px; margin-left: auto; }

/* ── 抽屉动画 ── */
.drawer-enter-active, .drawer-leave-active {
  transition: transform 0.3s cubic-bezier(0.22,1,0.36,1);
}
.drawer-enter-from, .drawer-leave-to { transform: translateY(100%); }

/* ── 面板动画 ── */
.panel-slide-enter-active, .panel-slide-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.panel-slide-enter-from, .panel-slide-leave-to {
  opacity: 0; transform: translateX(10px);
}

/* ── 遮罩 ── */
.editor-overlay {
  position: absolute; inset: 0; z-index: 2000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(15,23,42,0.75); color: #e5e7eb; font-size: 14px;
}
.editor-overlay--error { color: #fecaca; }

:deep(.leaflet-container) { width: 100%; height: 100%; background: transparent; }
:deep(.annotation-marker) { background: transparent; border: none; }

@media (max-width: 768px) {
  .sidebar { width: 120px; }
  .edit-panel { width: 240px; right: 8px; }
  .color-swatch { width: 30px; height: 38px; }
}
</style>
