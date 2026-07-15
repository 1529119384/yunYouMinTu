<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'

const overallImage = '/webp/总图.webp'
const floor1Image = '/webp/1层.webp'
const floor2Image = '/webp/2层.webp'
const floor3Image = '/webp/3层.webp'
const floor4Image = '/webp/4层.webp'
const floor5Image = '/webp/5层.webp'
const floor6Image = '/webp/6层.webp'
const floor7Image = '/webp/7层.webp'
const GUIDE_WIDTH = 5448
const GUIDE_HEIGHT = 3537
const LEGACY_VIEWBOX_SIZE = 1600
const ALPHA_MAP_SCALE = 0.25
// 取点调试工具暂时关闭；需要重新取点时改为 true。
const HOTSPOT_PICKER_VISIBLE = false

function scaleLegacyHotspots(points) {
  const scale = GUIDE_WIDTH / LEGACY_VIEWBOX_SIZE
  return points
    .split(/\s+/)
    .map((point) => point.split(',').map((value) => Number(value) * scale).join(','))
    .join(' ')
}

/**
 * 图片叠合微调区：
 * offsetX / offsetY 支持负数，单位为 px。
 * 如果某层没有完全对齐，只需要修改这里，不需要动模板和 CSS。
 * hotspots 使用 1600 x 1600 原图坐标，可按建筑立面继续微调。
 */
const floors = [
  { id: 7, label: '7F', name: '七层', targetFloorId: 'floor-7', image: floor7Image, offsetX: 0, offsetY: 0, hotspots: '517,497 913,694 1211,553 1210,601 912,739 516,540' },
  { id: 6, label: '6F', name: '六层', targetFloorId: 'floor-6', image: floor6Image, offsetX: 0, offsetY: 0, hotspots: '517,537 913,734 1211,593 1210,641 912,779 516,580' },
  { id: 5, label: '5F', name: '五层', targetFloorId: 'floor-5', image: floor5Image, offsetX: 0, offsetY: 0, hotspots: '517,577 913,774 1211,633 1210,681 912,819 516,620' },
  { id: 4, label: '4F', name: '四层', targetFloorId: 'floor-4', image: floor4Image, offsetX: 0, offsetY: 0, hotspots: '517,617 913,814 1211,673 1210,721 912,859 516,660' },
  { id: 3, label: '3F', name: '三层', targetFloorId: 'floor-3', image: floor3Image, offsetX: 0, offsetY: 0, hotspots: '517,657 913,854 1211,713 1210,761 912,899 516,700' },
  { id: 2, label: '2F', name: '二层', targetFloorId: 'floor-2', image: floor2Image, offsetX: 0, offsetY: 0, hotspots: '517,697 913,894 1211,753 1210,801 912,939 516,740' },
  { id: 1, label: '1F', name: '一层', targetFloorId: 'floor-1', image: floor1Image, offsetX: 0, offsetY: 0, hotspots: '517,737 913,934 1211,793 1210,841 912,979 516,780' },
].map((floor) => ({ ...floor, hotspots: scaleLegacyHotspots(floor.hotspots) }))

const router = useRouter()
const overallImageRef = ref(null)
const activeFloorId = ref(null)
const pickerEnabled = ref(false)
const cursorPoint = ref(null)
const pickedPoints = ref([])
const copyFeedback = ref('')
const activeFloor = computed(() => floors.find((floor) => floor.id === activeFloorId.value))
const pickerHotspots = computed(() => pickedPoints.value.map(({ x, y }) => `${x},${y}`).join(' '))
const pickerConfigText = computed(() => `hotspots: '${pickerHotspots.value}'`)
const pickerSvgPoints = computed(() => {
  const scale = GUIDE_WIDTH / LEGACY_VIEWBOX_SIZE
  return pickedPoints.value.map(({ x, y }) => `${x * scale},${y * scale}`).join(' ')
})
const hotspotPolygons = new Map(
  floors.map((floor) => [
    floor.id,
    floor.hotspots.split(/\s+/).map((point) => point.split(',').map(Number)),
  ]),
)

let overallAlpha = null
let alphaWidth = 0
let alphaHeight = 0
let pointerFrame = 0
let pendingPointerPoint = null

function showFloor(floorId) {
  activeFloorId.value = floorId
}

function resetFloor() {
  activeFloorId.value = null
}

function enterFloorGuide(floor) {
  router.push({ name: 'floor-map', params: { floorId: floor.targetFloorId } })
}

function enterActiveFloor() {
  if (activeFloor.value) enterFloorGuide(activeFloor.value)
}

function togglePicker() {
  pickerEnabled.value = !pickerEnabled.value
  cursorPoint.value = null
  resetFloor()
}

function toLegacyPoint(x, y) {
  const scale = GUIDE_WIDTH / LEGACY_VIEWBOX_SIZE
  return {
    x: Math.round(x / scale),
    y: Math.round(y / scale),
  }
}

async function copyText(text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    textarea.remove()
  }

  copyFeedback.value = '已复制到剪贴板'
  window.setTimeout(() => { copyFeedback.value = '' }, 1400)
}

function handleHotspotClick() {
  if (!pickerEnabled.value) {
    enterActiveFloor()
    return
  }
  if (!cursorPoint.value) return

  pickedPoints.value.push({ ...cursorPoint.value })
  copyText(pickerConfigText.value)
}

function undoPickerPoint() {
  pickedPoints.value.pop()
  if (pickedPoints.value.length) copyText(pickerConfigText.value)
}

function clearPickerPoints() {
  pickedPoints.value = []
  copyFeedback.value = '已清空取点'
}

function prepareAlphaMap() {
  const image = overallImageRef.value
  if (!image?.naturalWidth || !image?.naturalHeight) return

  const canvas = document.createElement('canvas')
  // 命中图不需要保留渲染图的全部像素，缩小后可显著降低内存和读取开销。
  alphaWidth = Math.ceil(image.naturalWidth * ALPHA_MAP_SCALE)
  alphaHeight = Math.ceil(image.naturalHeight * ALPHA_MAP_SCALE)
  canvas.width = alphaWidth
  canvas.height = alphaHeight

  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (!context) return

  context.drawImage(image, 0, 0, alphaWidth, alphaHeight)
  overallAlpha = context.getImageData(0, 0, alphaWidth, alphaHeight).data
}

function isPointInPolygon(x, y, polygon) {
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i]
    const [xj, yj] = polygon[j]
    const crosses = ((yi > y) !== (yj > y))
      && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi)
    if (crosses) inside = !inside
  }
  return inside
}

function isOverallImageOpaque(x, y) {
  if (!overallAlpha || !alphaWidth || !alphaHeight) return true

  const pixelX = Math.min(alphaWidth - 1, Math.max(0, Math.floor(x / GUIDE_WIDTH * alphaWidth)))
  const pixelY = Math.min(alphaHeight - 1, Math.max(0, Math.floor(y / GUIDE_HEIGHT * alphaHeight)))
  const alphaIndex = (pixelY * alphaWidth + pixelX) * 4 + 3
  return overallAlpha[alphaIndex] > 16
}

function processHotspotPoint(x, y) {
  if (pickerEnabled.value) {
    cursorPoint.value = toLegacyPoint(x, y)
    activeFloorId.value = null
    return
  }

  if (x < 0 || x > GUIDE_WIDTH || y < 0 || y > GUIDE_HEIGHT || !isOverallImageOpaque(x, y)) {
    resetFloor()
    return
  }

  const floor = floors.find((item) => isPointInPolygon(x, y, hotspotPolygons.get(item.id)))
  activeFloorId.value = floor?.id ?? null
}

function handleHotspotPointer(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  if (!rect.width || !rect.height) return

  const point = {
    x: (event.clientX - rect.left) / rect.width * GUIDE_WIDTH,
    y: (event.clientY - rect.top) / rect.height * GUIDE_HEIGHT,
  }

  // 点击时立即更新命中层；移动时限制为每个绘制帧最多计算一次。
  if (event.type === 'pointerdown') {
    processHotspotPoint(point.x, point.y)
    return
  }

  pendingPointerPoint = point
  if (pointerFrame) return
  pointerFrame = window.requestAnimationFrame(() => {
    pointerFrame = 0
    if (!pendingPointerPoint) return
    processHotspotPoint(pendingPointerPoint.x, pendingPointerPoint.y)
    pendingPointerPoint = null
  })
}

function handleHotspotLeave() {
  if (pointerFrame) window.cancelAnimationFrame(pointerFrame)
  pointerFrame = 0
  pendingPointerPoint = null
  cursorPoint.value = null
  if (!pickerEnabled.value) resetFloor()
}

onBeforeUnmount(() => {
  if (pointerFrame) window.cancelAnimationFrame(pointerFrame)
})
</script>

<template>
  <main class="building-guide">
    <header class="guide-header">
      <div>
        <p class="eyebrow">SPATIAL GUIDE · 空间导览</p>
        <h1>楼层空间导览</h1>
      </div>
      <p class="guide-tip">
        将鼠标移至建筑立面的不同楼层
        <span>查看对应楼层轴测图</span>
      </p>
    </header>

    <section class="guide-stage" @mouseleave="resetFloor">
      <div class="building-canvas">
        <div class="image-stack" :class="{ 'is-exploring': activeFloor }">
          <img
            ref="overallImageRef"
            class="building-image overall-image"
            :src="overallImage"
            alt="楼宇建筑总图"
            draggable="false"
            @load="prepareAlphaMap"
          >

          <img
            v-for="floor in floors"
            v-show="activeFloorId === floor.id"
            :key="floor.id"
            class="building-image floor-image"
            :src="floor.image"
            :alt="`${floor.name}轴测图`"
            :style="{
              '--floor-offset-x': `${floor.offsetX}px`,
              '--floor-offset-y': `${floor.offsetY}px`,
              zIndex: 20 + floor.id,
            }"
            draggable="false"
          >

          <svg
            class="floor-hotspots"
            :viewBox="`0 0 ${GUIDE_WIDTH} ${GUIDE_HEIGHT}`"
            preserveAspectRatio="xMidYMid meet"
            role="group"
            aria-label="建筑楼层选择区域"
            :class="{ 'has-active-floor': activeFloor, 'is-picking': pickerEnabled }"
            @pointermove="handleHotspotPointer"
            @pointerdown="handleHotspotPointer"
            @pointerleave="handleHotspotLeave"
            @click="handleHotspotClick"
          >
            <polygon
              v-for="floor in floors"
              :key="floor.id"
              class="floor-hotspot"
              :class="{ 'is-active': activeFloorId === floor.id }"
              :points="floor.hotspots"
              tabindex="0"
              :aria-label="`查看${floor.name}，点击进入楼层地图`"
              @focus="showFloor(floor.id)"
              @blur="resetFloor"
              @keydown.enter.prevent="enterFloorGuide(floor)"
              @keydown.space.prevent="enterFloorGuide(floor)"
            />

            <polyline
              v-if="pickerEnabled && pickedPoints.length"
              class="picker-outline"
              :points="pickerSvgPoints"
            />
            <circle
              v-for="(point, index) in pickedPoints"
              :key="`picker-${index}`"
              class="picker-point"
              :cx="point.x * GUIDE_WIDTH / LEGACY_VIEWBOX_SIZE"
              :cy="point.y * GUIDE_WIDTH / LEGACY_VIEWBOX_SIZE"
              r="18"
            />
          </svg>

          <aside
            v-if="HOTSPOT_PICKER_VISIBLE"
            class="hotspot-picker"
            :class="{ 'is-enabled': pickerEnabled }"
          >
            <button class="picker-toggle" type="button" @click="togglePicker">
              {{ pickerEnabled ? '退出取点' : '取点模式' }}
            </button>

            <template v-if="pickerEnabled">
              <p class="picker-help">移动查看坐标，左键追加并复制</p>
              <strong class="picker-coordinate">
                {{ cursorPoint ? `${cursorPoint.x},${cursorPoint.y}` : '—,—' }}
              </strong>
              <code class="picker-result">{{ pickerConfigText }}</code>
              <div class="picker-actions">
                <button type="button" :disabled="!pickedPoints.length" @click="undoPickerPoint">
                  撤销
                </button>
                <button type="button" :disabled="!pickedPoints.length" @click="clearPickerPoints">
                  清空
                </button>
                <button type="button" :disabled="!pickedPoints.length" @click="copyText(pickerConfigText)">
                  复制
                </button>
              </div>
              <span v-if="copyFeedback" class="copy-feedback">{{ copyFeedback }}</span>
            </template>
          </aside>

          <div v-if="activeFloor" class="active-floor-badge" aria-live="polite">
            <strong>{{ activeFloor.label }}</strong>
            <span>{{ activeFloor.name }}轴测图</span>
          </div>
        </div>
      </div>

      <nav class="floor-nav" aria-label="楼层导航">
        <p>FLOOR</p>
        <button
          v-for="floor in floors"
          :key="floor.id"
          class="floor-button"
          :class="{ 'is-active': activeFloorId === floor.id }"
          type="button"
          @mouseenter="showFloor(floor.id)"
          @focus="showFloor(floor.id)"
          @click="enterFloorGuide(floor)"
        >
          <span>{{ floor.label }}</span>
          <small>{{ floor.name }}</small>
        </button>
        <button class="reset-button" type="button" @click="resetFloor">
          总图
        </button>
      </nav>
    </section>
  </main>
</template>

<style scoped>
.building-guide {
  --ink: #18211d;
  --muted: #6e7772;
  --accent: #b54d2e;
  min-height: 100%;
  box-sizing: border-box;
  overflow: hidden;
  color: var(--ink);
  background:
    radial-gradient(circle at 72% 40%, rgb(213 224 216 / 52%), transparent 32rem),
    linear-gradient(135deg, #f6f3ec 0%, #ecefe9 100%);
}

.guide-header {
  position: relative;
  z-index: 40;
  display: flex;
  align-items: end;
  justify-content: space-between;
  max-width: 1440px;
  margin: 0 auto;
  padding: 32px 48px 0;
  box-sizing: border-box;
}

.eyebrow,
.floor-nav > p {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.22em;
}

h1 {
  margin: 0;
  font-family: "Noto Serif SC", "Songti SC", serif;
  font-size: clamp(30px, 3.3vw, 54px);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.guide-tip {
  margin: 0 0 5px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
  text-align: right;
}

.guide-tip span {
  display: block;
  color: var(--ink);
}

.guide-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 82px;
  gap: 24px;
  align-items: center;
  width: min(1460px, 100%);
  min-height: calc(100vh - 117px);
  margin: 0 auto;
  padding: 0 42px 30px 24px;
  box-sizing: border-box;
}

.building-canvas {
  width: 100%;
  min-width: 0;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(
    90deg,
    transparent 0%,
    #000 4%,
    #000 96%,
    transparent 100%
  );
  mask-image: linear-gradient(
    90deg,
    transparent 0%,
    #000 4%,
    #000 96%,
    transparent 100%
  );
}

.image-stack {
  position: relative;
  left: 50%;
  display: flex;
  width: min(150%, calc((100vh - 90px) * 1.72));
  min-width: 0;
  aspect-ratio: 5448 / 3537;
  margin: -38px 0 -68px;
  isolation: isolate;
  transform: translateX(-50%);
}

.building-image {
  display: block;
  flex: 0 0 100%;
  width: 100%;
  height: auto;
  object-fit: contain;
  user-select: none;
  transition: opacity 280ms ease, filter 280ms ease;
}

.overall-image {
  position: relative;
  z-index: 10;
  opacity: 1;
}

.is-exploring .overall-image {
  opacity: 0.22;
  filter: saturate(0.65);
}

.floor-image {
  position: relative;
  /* 负 margin-left 将同尺寸楼层图拉回总图上方；两个变量用于逐层微调。 */
  margin-top: var(--floor-offset-y, 0px);
  margin-left: calc(-100% + var(--floor-offset-x, 0px));
  pointer-events: none;
  animation: reveal-floor 260ms ease both;
}

.floor-hotspots {
  position: absolute;
  inset: 0;
  z-index: 50;
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
  cursor: default;
  -webkit-mask-image: url('/webp/总图.webp');
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-position: center;
  -webkit-mask-size: 100% 100%;
  mask-image: url('/webp/总图.webp');
  mask-mode: alpha;
  mask-repeat: no-repeat;
  mask-position: center;
  mask-size: 100% 100%;
}

.floor-hotspots.has-active-floor {
  cursor: pointer;
}

.floor-hotspots.is-picking {
  cursor: crosshair;
}

.floor-hotspot {
  fill: rgb(181 77 46 / 0%);
  stroke: rgb(181 77 46 / 0%);
  stroke-width: 3;
  pointer-events: none;
  outline: none;
  transition: fill 160ms ease, stroke 160ms ease;
}

.floor-hotspot:hover,
.floor-hotspot:focus,
.floor-hotspot.is-active {
  fill: rgb(181 77 46 / 7%);
  stroke: rgb(181 77 46 / 34%);
}

.picker-outline {
  fill: rgb(255 203 74 / 12%);
  stroke: #ffcb4a;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-linejoin: round;
  pointer-events: none;
}

.picker-point {
  fill: #ffcb4a;
  stroke: #18211d;
  stroke-width: 6;
  pointer-events: none;
}

.hotspot-picker {
  position: absolute;
  top: 12%;
  left: 5%;
  z-index: 80;
  width: 220px;
  padding: 8px;
  color: white;
  background: rgb(24 33 29 / 82%);
  border: 1px solid rgb(255 255 255 / 12%);
  border-radius: 4px;
  box-sizing: border-box;
  backdrop-filter: blur(10px);
}

.hotspot-picker.is-enabled {
  padding: 10px;
}

.picker-toggle,
.picker-actions button {
  border: 0;
  color: white;
  background: transparent;
  cursor: pointer;
}

.picker-toggle {
  width: 100%;
  padding: 6px 8px;
  color: #ffdb7b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.picker-help {
  margin: 8px 0 4px;
  color: rgb(255 255 255 / 58%);
  font-size: 10px;
}

.picker-coordinate {
  display: block;
  color: #ffdb7b;
  font-family: Consolas, monospace;
  font-size: 20px;
}

.picker-result {
  display: block;
  max-height: 62px;
  margin-top: 7px;
  padding: 7px;
  overflow: auto;
  color: rgb(255 255 255 / 76%);
  background: rgb(0 0 0 / 20%);
  font-family: Consolas, monospace;
  font-size: 9px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.picker-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin-top: 7px;
}

.picker-actions button {
  padding: 5px;
  background: rgb(255 255 255 / 10%);
  border-radius: 2px;
  font-size: 10px;
}

.picker-actions button:hover:not(:disabled) {
  background: rgb(255 255 255 / 18%);
}

.picker-actions button:disabled {
  cursor: default;
  opacity: 0.35;
}

.copy-feedback {
  display: block;
  margin-top: 6px;
  color: #9ee0c3;
  font-size: 10px;
  text-align: center;
}

.active-floor-badge {
  position: absolute;
  right: 8%;
  bottom: 18%;
  z-index: 60;
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 9px 13px;
  color: white;
  background: rgb(24 33 29 / 88%);
  border-radius: 2px;
  pointer-events: none;
  backdrop-filter: blur(8px);
}

.active-floor-badge strong {
  font-size: 17px;
  letter-spacing: 0.08em;
}

.active-floor-badge span {
  color: rgb(255 255 255 / 72%);
  font-size: 11px;
}

.floor-nav {
  position: relative;
  z-index: 70;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-left: 20px;
  border-left: 1px solid rgb(24 33 29 / 14%);
}

.floor-button,
.reset-button {
  width: 62px;
  border: 0;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease, transform 160ms ease;
}

.floor-button {
  display: grid;
  grid-template-columns: 1fr;
  padding: 7px 8px;
  text-align: left;
  border-radius: 2px;
}

.floor-button span {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.floor-button small {
  margin-top: 1px;
  font-size: 10px;
  opacity: 0.65;
}

.floor-button:hover,
.floor-button:focus-visible,
.floor-button.is-active {
  color: white;
  background: var(--accent);
  outline: none;
  transform: translateX(-5px);
}

.reset-button {
  margin-top: 6px;
  padding: 8px;
  border-top: 1px solid rgb(24 33 29 / 14%);
  font-size: 11px;
}

.reset-button:hover,
.reset-button:focus-visible {
  color: var(--accent);
  outline: none;
}

@keyframes reveal-floor {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (max-width: 820px) {
  .guide-header {
    padding: 24px 22px 0;
  }

  .guide-tip {
    display: none;
  }

  .guide-stage {
    display: flex;
    min-height: auto;
    padding: 20px 16px 24px;
    flex-direction: column;
  }

  .building-canvas {
    width: calc(100% + 32px);
    margin-inline: -16px;
    -webkit-mask-image: linear-gradient(
      90deg,
      transparent 0%,
      #000 8%,
      #000 92%,
      transparent 100%
    );
    mask-image: linear-gradient(
      90deg,
      transparent 0%,
      #000 8%,
      #000 92%,
      transparent 100%
    );
  }

  .image-stack {
    width: 145%;
    min-width: 0;
    margin: -4vw 0 -7vw;
  }

  .hotspot-picker {
    top: 7%;
    left: 3%;
    width: 190px;
  }

  .floor-nav {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    width: 100%;
    padding: 14px 0 0;
    border-top: 1px solid rgb(24 33 29 / 14%);
    border-left: 0;
  }

  .floor-nav > p {
    display: none;
  }

  .floor-button,
  .reset-button {
    width: auto;
  }

  .floor-button:hover,
  .floor-button:focus-visible,
  .floor-button.is-active {
    transform: translateY(-3px);
  }

  .reset-button {
    margin: 0;
    border-top: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .building-image,
  .floor-hotspot,
  .floor-button {
    transition: none;
    animation: none;
  }
}
</style>
