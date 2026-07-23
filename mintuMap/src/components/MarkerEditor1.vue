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
        <button class="sidebar__btn" @click="triggerImport">
          <span class="sidebar__icon">📥</span>
          <span>导入</span>
        </button>
        <input ref="fileInputRef" type="file" accept=".json" style="display:none" @change="importConfig" />
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
            <!-- 标点样式：7 种 SVG 颜色图标（内联 SVG 避免加载失败） -->
            <label class="field">
              <span class="field__label">标点样式</span>
              <div class="color-grid">
                <div v-for="opt in COLOR_OPTIONS" :key="opt.value"
                     class="color-swatch"
                     :class="{ 'color-swatch--active': selectedMarker.color === opt.value }"
                     :style="{ '--swatch-color': opt.tagBg }"
                     :title="opt.label"
                     @click="pickColor(opt.value)">
                   <svg viewBox="0 0 104.6 144.9" class="color-swatch__icon">
                    <path d="M52.3,0C23.5,0,0,24.1,0,53.8s28,66,49.5,89.8c1.5,1.7,4.1,1.7,5.6,0C76.6,120.8,104.6,86.1,104.6,53.8S81.2,0,52.3,0z" fill="#fff"/>
                    <circle cx="52.3" cy="53.8" r="20" :fill="opt.tagBg"/>
                  </svg>

                </div>
              </div>
            </label>
            <!-- 全景关联：选择对应 360° 场景 -->
            <label class="field">
              <span class="field__label">全景关联</span>
              <select v-model="selectedMarker.sceneId" class="field__input" @change="onMarkerChange">
                <option value="">无关联</option>
                <option v-for="n in 116" :key="n" :value="'scene' + n">scene{{ n }}</option>
              </select>
            </label>
            <!-- 标点大小 -->
            <label class="field">
              <span class="field__label">标点大小</span>
              <div class="size-row">
                <input type="range" min="0.3" max="2" step="0.05" :value="selectedMarker.size || 1"
                       @input="onSizeChange($event.target.value)" class="size-slider">
                <span class="size-value">{{ (selectedMarker.size || 1).toFixed(2) }}×</span>
              </div>
            </label>
            <div class="field__actions">
              <button class="btn btn--danger" @click="removeMarker">删除</button>
            </div>
          </template>

          <!-- 默认提示 -->
          <template v-else>
            <p class="edit-panel__hint">选择左侧工具后点击地图添加</p>
          </template>
        </div>
      </div>
    </transition>

    <!-- 状态提示 -->
    <div v-if="tool" class="tool-hint">
      点击地图放置标点 · 按 ESC 取消
    </div>

    <div v-if="loading" class="editor-overlay">加载中...</div>
    <div v-else-if="error" class="editor-overlay editor-overlay--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// ── 常量 ──────────────────────────────────────────────

const COLOR_OPTIONS = [
  { value: 'blue',     label: '通用',   tagBg: '#66cccc', inline: true },
  { value: 'blueDark', label: '重要',   tagBg: '#1f296a', inline: true },
  { value: 'gray',     label: '附属',   tagBg: '#3b3b3b', inline: true },
  { value: 'red',      label: '服务',   tagBg: '#cc6666', inline: true },
  { value: 'orange',   label: '餐厅',   tagBg: '#d36839', inline: true },
  { value: 'gate',     label: '入口',   tagBg: '#1f296a', inline: true },
  { value: 'landmark', label: '地标',   tagBg: '#1f296a', inline: true },

]

const EMPTY_TILE = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs='

// ── Props ─────────────────────────────────────────────

const props = defineProps({
  floors: { type: Array, required: true },
  backgroundColor: { type: String, default: '#0f172a' },
})

// ── 状态 ──────────────────────────────────────────────

const mapRef = ref(null)
const fileInputRef = ref(null)
const loading = ref(true)
const error = ref('')
const tool = ref(null)
const editingType = ref('')
const selectedId = ref('')
const currentFloorId = ref(props.floors[0]?.id || '')
const floorData = ref(new Map())

let map = null
const tileLayers = {}
const markerGroups = {}

// ── 计算属性 ──────────────────────────────────────────

const currentFloorData = computed(() => floorData.value.get(currentFloorId.value) || { markers: [], annotations: [] })

const selectedMarker = computed(() => {
  if (editingType.value !== 'marker') return null
  return currentFloorData.value.markers.find(m => m.id === selectedId.value) || null
})

const showPanel = computed(() => editingType.value === 'marker')

const panelTitle = computed(() => '编辑标点')

// ── 工具函数 ──────────────────────────────────────────

function deriveBaseUrl(urlTemplate) {
  return urlTemplate.replace(/\/\{z\}\/\{x\}\/\{y\}\.\w+$/, '')
}

// ── Leaflet 图标（内联 SVG，避免外部 SVG 加载失败） ──

const PIN_FILLS = {
  blue: '#66cccc', blueDark: '#1f296a', gray: '#3b3b3b',
  red: '#cc6666', orange: '#d36839', gate: '#1f296a', landmark: '#1f296a',
}

function createMarkerIcon(data, active = false) {
  const fill = PIN_FILLS[data.color] || '#66cccc'
  const s = data.size || 1
  const w = (active ? 52 : 36) * s
  const h = (active ? 72 : 50) * s
  const html = `<svg viewBox="0 0 104.6 144.9" width="${w}" height="${h}">
    <path d="M52.3,0C23.5,0,0,24.1,0,53.8s28,66,49.5,89.8c1.5,1.7,4.1,1.7,5.6,0C76.6,120.8,104.6,86.1,104.6,53.8S81.2,0,52.3,0z" fill="#fff"/>
    <circle cx="52.3" cy="53.8" r="20" fill="${fill}"/>
  </svg>`
  return L.divIcon({
    html,
    className: 'editor-pin-marker',
    iconSize: [w, h],
    iconAnchor: [w / 2, h],
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
  addMarker(e.latlng)
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
    sceneId: '',
    size: 1,
  }
  currentFloorData.value.markers.push(data)
  renderMarker(data)
  selectItem(data.id, 'marker')
  saveToLocalStorage()
}

function removeMarker() {
  if (!selectedMarker.value) return
  const id = selectedMarker.value.id
  currentFloorData.value.markers = currentFloorData.value.markers.filter(m => m.id !== id)
  const group = markerGroups[currentFloorId.value]
  if (group) group.eachLayer(l => { if (l._data?.id === id) group.removeLayer(l) })
  closePanel()
  saveToLocalStorage()
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
  marker.on('dragend', () => { data.position = [marker.getLatLng().lat, marker.getLatLng().lng]; saveToLocalStorage() })
  marker._data = data
  group.addLayer(marker)
}

// ── 颜色选取 + 标点变更时更新地图图标 ──────────────

function updateMarkerIcon(markerData) {
  if (!markerData || !map) return
  const group = markerGroups[currentFloorId.value]
  if (!group) return
  group.eachLayer(layer => {
    if (layer._data?.id === markerData.id) {
      layer.setIcon(createMarkerIcon(markerData, false))
    }
  })
}

function pickColor(color) {
  if (!selectedMarker.value) return
  selectedMarker.value.color = color
  updateMarkerIcon(selectedMarker.value)
  saveToLocalStorage()
}

function onMarkerChange() {
  if (!selectedMarker.value) return
  saveToLocalStorage()
}

function onSizeChange(val) {
  if (!selectedMarker.value) return
  const s = parseFloat(val)
  if (isNaN(s)) return
  selectedMarker.value.size = s
  updateMarkerIcon(selectedMarker.value)
  saveToLocalStorage()
}

// ── 显式保存到 localStorage ────────────────────────

function saveToLocalStorage() {
  const data = {}
  floorData.value.forEach((v, k) => { data[k] = v })
  localStorage.setItem('mintumap-editor-data', JSON.stringify(data))
}

// ── 选择 ──────────────────────────────────────────────

function selectItem(id, type) {
  selectedId.value = id
  editingType.value = type
}

function closePanel() {
  saveToLocalStorage()
  selectedId.value = ''
  editingType.value = ''
}

// ── 楼层切换 ──────────────────────────────────────────

function switchFloor(id) {
  currentFloorId.value = id
  closePanel()
  // 隐藏所有已显示图层，再显示当前楼层
  Object.keys(tileLayers).forEach(fid => {
    if (map.hasLayer(tileLayers[fid])) map.removeLayer(tileLayers[fid])
    if (markerGroups[fid]) map.removeLayer(markerGroups[fid])
  })
  if (tileLayers[id]) tileLayers[id].addTo(map)
  if (markerGroups[id]) markerGroups[id].addTo(map)
}

// ── 清空 ──────────────────────────────────────────────

function clearAll() {
  const data = currentFloorData.value
  data.markers = []
  data.annotations = []
  const mg = markerGroups[currentFloorId.value]
  if (mg) mg.clearLayers()
  closePanel()
  saveToLocalStorage()
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
          color: m.color, label: [...m.label], text: m.text, type: m.type, sceneId: m.sceneId || '',
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

// ── 导入 ──────────────────────────────────────────────

function triggerImport() {
  fileInputRef.value?.click()
}

function importConfig(e) {
  const file = e.target?.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    try {
      const imported = JSON.parse(ev.target?.result)
      if (!imported?.floors || !Array.isArray(imported.floors)) {
        alert('导入失败：文件格式不正确，缺少 floors 数组')
        return
      }
      // 按楼层匹配 ID 写入数据
      let count = 0
      for (const f of imported.floors) {
        if (floorData.value.has(f.id)) {
          floorData.value.set(f.id, {
            markers: f.markers || [],
            annotations: f.annotations || [],
          })
          count += (f.markers || []).length
        }
      }
      markerGroups[currentFloorId.value]?.clearLayers()
      // 重新渲染当前楼层所有标点
      const floor = props.floors.find(f => f.id === currentFloorId.value)
      if (floor) renderFloorMarkers(floor)
      saveToLocalStorage()
      alert(`导入成功：${count} 个标点`)
    } catch {
      alert('导入失败：无法解析 JSON 文件')
    }
  }
  reader.readAsText(file)
  // 重置 input 以便重复选择同一文件
  e.target.value = ''
}

function renderFloorMarkers(floor) {
  const data = floorData.value.get(floor.id)
  if (!data) return
  const group = markerGroups[floor.id]
  if (!group) return
  group.clearLayers()
  for (const m of data.markers || []) {
    const latlng = L.latLng(m.position[0], m.position[1])
    const marker = L.marker(latlng, {
      draggable: true,
      icon: createMarkerIcon(m, m.id === selectedId.value),
      riseOnHover: true,
    })
    marker.on('click', (e) => { L.DomEvent.stopPropagation(e); selectItem(m.id, 'marker') })
    marker.on('dragend', () => { m.position = [marker.getLatLng().lat, marker.getLatLng().lng]; saveToLocalStorage() })
    marker._data = m
    group.addLayer(marker)
  }
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

    // 从 localStorage 恢复上次编辑的数据
    function loadSavedData() {
      try {
        const raw = localStorage.getItem('mintumap-editor-data')
        if (!raw) return {}
        return JSON.parse(raw)
      } catch { return {} }
    }
    const savedData = loadSavedData()

    // 加载所有楼层 manifest 并创建图层
    for (const floor of props.floors) {
      // 初始化数据（优先用 localStorage 保存的，否则新建空数据）
      floorData.value.set(floor.id, savedData[floor.id] || { markers: [], annotations: [] })

      // 创建标点图层组（拖拽标点用）
      markerGroups[floor.id] = L.layerGroup()

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

    // 渲染所有楼层中已有的标点（从 localStorage 恢复）
    for (const floor of props.floors) {
      renderFloorMarkers(floor)
    }

    // 设置全局 bounds（所有楼层 16384×16384）
    const globalSW = map.unproject([0, 16384], 5)
    const globalNE = map.unproject([16384, 0], 5)
    map.setMaxBounds(L.latLngBounds(globalSW, globalNE).pad(0.1))

    // 显示默认楼层切片底图和标点
    if (tileLayers[currentFloorId.value]) tileLayers[currentFloorId.value].addTo(map)
    markerGroups[currentFloorId.value]?.addTo(map)

    const firstBounds = tileLayers[currentFloorId.value]?.options?.bounds
    if (firstBounds) map.fitBounds(firstBounds, { animate: false })

    map.invalidateSize(false)
    map.on('click', onMapClick)
    document.addEventListener('keydown', onKeyDown)

    // 初始化完成后保存一次，确认数据持久化
    saveToLocalStorage()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

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
.color-swatch__icon { width: 26px; height: 32px; object-fit: contain; }

/* ── 标点大小滑块 ── */
.size-row { display: flex; align-items: center; gap: 8px; }
.size-slider {
  flex: 1; height: 4px; -webkit-appearance: none; appearance: none;
  background: rgba(255,255,255,0.15); border-radius: 2px; outline: none;
  cursor: pointer;
}
.size-slider::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 14px; height: 14px; border-radius: 50%;
  background: #2563eb; border: none; cursor: pointer;
}
.size-slider::-moz-range-thumb {
  width: 14px; height: 14px; border-radius: 50%;
  background: #2563eb; border: none; cursor: pointer;
}
.size-value {
  min-width: 40px; text-align: right;
  font-size: 12px; color: #94a3b8; font-variant-numeric: tabular-nums;
}

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
:deep(.editor-pin-marker) { background: transparent; border: none; }

@media (max-width: 768px) {
  .sidebar { width: 120px; }
  .edit-panel { width: 240px; right: 8px; }
  .color-swatch { width: 30px; height: 38px; }
}
</style>
