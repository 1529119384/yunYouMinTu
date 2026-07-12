# mintuMap 标点系统设计

## 数据格式（对齐 ysumc 实用设计）

```js
{
  project: {
    title: "《闽图建筑导览》",
    description: "福建省图书馆建筑可视化..."
  },
  markers: [
    {
      id: "marker-1",
      position: [5809, 3072],    // 像素坐标
      title: "图书馆主楼",
      color: "blue",             // 自动映射 SVG 颜色
      label: ["图书馆"],         // 抽屉标签（数组）
      text: "这里是描述...",      // 支持 <br> HTML
      type: "building"           // building / entrance / service / landmark
    }
  ]
}
```

## 颜色系统

| color 值 | SVG 文件 | 圆点颜色 | 用途 | 标签背景色 |
|----------|---------|---------|------|-----------|
| `blue` | `pin_blue.svg` | 青色 #66cccc | 学院/建筑/通用 | 青色 |
| `blueDark` | `pin_blueDark.svg` | 深蓝 #1f296a | 重要建筑 | 深蓝 |
| `gray` | `pin_gray.svg` | 深灰 #3b3b3b | 宿舍/附属建筑 | 深灰 |
| `red` | `pin_red.svg` | 红色 #cc6666 | 服务设施 | 红色 |
| `orange` | `pin_orange.svg` | 橙色 #d36839 | 餐厅/餐饮 | 橙色 |
| `gate` | `pin_gate.svg` | 深蓝全填充 #1f296a | 入口/门 | 深蓝 |
| `landmark` | `pin_landmark.svg` | 深蓝底+白色旗帜 | 地标/特殊建筑 | 深蓝 |

颜色通过 `color` 字段自动映射 SVG 文件，不需要手动管理图标。

### 颜色映射代码

```js
const COLOR_ICON_MAP = {
  blue:     '/pin_blue.svg',
  blueDark: '/pin_blueDark.svg',
  gray:     '/pin_gray.svg',
  red:      '/pin_red.svg',
  orange:   '/pin_orange.svg',
  gate:     '/pin_gate.svg',
  landmark: '/pin_landmark.svg',
}
```

### SVG 文件

所有 SVG 文件位于 `mintuMap/public/` 目录下，viewBox `0 0 104.6 144.9`，任意缩放清晰。

## type 枚举

- `building` — 建筑（学院、办公楼、教学楼）
- `entrance` — 入口/门
- `service` — 服务设施（快递、超市、浴池）
- `landmark` — 地标/特殊建筑

## 工作流

### 本地编辑
1. `npm run editor` → 打开编辑器页面
2. 在地图上点击添加标点
3. 选择颜色、输入标签和描述
4. 导出 → 下载 `markers.json`

### 构建硬编码
1. 将 `markers.json` 放到 `public/markers.json`
2. 运行 `npm run build` → JSON 被打包进产物
3. 或者运行 `npm run embed` → JSON 转为 JS 模块 import 进组件（零运行时请求）

## 编辑器 UI 改造计划

**文件：** `mintuMap/src/components/MarkerEditor1.vue`

### 右侧编辑面板字段

| 旧字段 | 新字段 | 说明 |
|--------|--------|------|
| `drawer.regionName` | `title` | 标点标题（input） |
| `drawer.navButtonText` | 删除 | 不需要 |
| `drawer.description1` + `drawer.description2` | `text` | 单个 textarea，支持 HTML |
| 无 | `color` | 下拉选择（7 种颜色） |
| 无 | `label` | 标签输入（回车添加，chip 显示，点击删除） |
| 无 | `type` | 下拉选择（building/entrance/service/landmark） |
| `style1` / `style2` | 删除 | 不再需要手动管理图标 |

### 项目抽屉字段

- `projectTitle` → `title`
- `projectDescription` → `description`

### 颜色选择器

```js
const COLOR_OPTIONS = [
  { value: 'blue',     label: '通用建筑', icon: '/pin_blue.svg' },
  { value: 'blueDark', label: '重要建筑', icon: '/pin_blueDark.svg' },
  { value: 'gray',     label: '宿舍/附属', icon: '/pin_gray.svg' },
  { value: 'red',      label: '服务设施', icon: '/pin_red.svg' },
  { value: 'orange',   label: '餐厅',     icon: '/pin_orange.svg' },
  { value: 'gate',     label: '入口/门',  icon: '/pin_gate.svg' },
  { value: 'landmark', label: '地标',     icon: '/pin_landmark.svg' },
]
```

### 标点图标

`createMarkerIcon()` 从 color 字段映射 SVG，选中状态用更大尺寸：
```js
function createMarkerIcon(markerData, active = false) {
  const iconUrl = COLOR_OPTIONS.find(c => c.value === markerData.color)?.icon || '/pin_blue.svg'
  const size = active ? [52, 72] : [36, 50]
  return L.icon({
    iconUrl,
    iconSize: size,
    iconAnchor: [size[0] / 2, size[1]],
    popupAnchor: [0, -size[1]],
  })
}
```

### 底部预览抽屉

对齐 ysumc 布局：
- 左栏：标题 h1 + 标签 span（彩色背景圆角）
- 右栏：描述文字
- 动画：已有的 `bottom-drawer-switch` transition

### 标签输入

- 输入框 + 回车添加标签
- 已有标签显示为彩色 chip，点击删除
- 支持多个标签

### 导出格式

```js
{
  project: { title, description },
  markers: [{ id, position, title, color, label, text, type }]
}
```

## 展示页面（Viewer）— 多楼层架构

### 建筑结构

```
7F  放映厅
6F
5F
4F
3F
2F  阅览室/儿童区
1F  大厅 / 阅览室/自习室
整体外观
```

每层楼独立 manifest（已切片，需重新生成）。

### 交互架构

**整体外观层：**
- 建筑外观 tile set
- 引出线/指引线标注（不是 SVG 标点）
  - 直线引出线：一根直线连到建筑
  - 弯折引出线：折一次或多次，避开建筑线条，末端写字
- 点击引出线 → 缩放动画进入对应楼层

**楼层内部层：**
- 楼层平面图 tile set
- SVG 水滴标点（pin_blue.svg 等）
- 标点点击显示抽屉详情
- ↑↓ 垂直滑动切换楼层
- "返回整体"按钮 → 缩放动画退回

### 动画流

```
整体外观（引出线标注）
  │ 点击引出线
  │ flyTo 缩放 + tile layer 切换
  ▼
1F 大厅（SVG 标点）
  │ ↑↓ 垂直滑动
  ▼
2F 儿童区
  │ 点击"返回"
  │ flyTo 缩放 + tile layer 切换
  ▼
整体外观
```

### 楼层数据格式

```js
const floors = [
  {
    id: 'overall',
    name: '整体外观',
    manifestUrl: '/api/tiles/xxx/manifest',
    // 引出线配置
    annotations: [
      {
        id: 'ann-1',
        targetFloor: 'floor-1',
        anchor: [x, y],           // 建筑上的锚点坐标
        labelPos: [x, y],         // 文字终点坐标
        bends: [[x1,y1]],         // 中间折点（空则为直线）
        label: '1F 大厅',
      },
      // ...
    ],
  },
  {
    id: 'floor-1',
    name: '1F 大厅',
    manifestUrl: '/api/tiles/yyy/manifest',
    markers: [
      { id: 'm1', position: [x,y], title: '服务台', color: 'blue', label: ['服务'], text: '...', type: 'service' },
    ],
  },
  // ...
]
```

### 整体外观标注 — 双圈圆形标记

由于缩放时引出线长度会变化，改用**双圈白色圆形标记**（缩放无关）：

```
默认状态：外圈白色半透明 + 内圈实心白色
hover/选中：外圈更透明 + 内圈变为对应颜色
```

SVG 结构：
```svg
<svg width="60" height="60" viewBox="0 0 60 60">
  <circle cx="30" cy="30" r="28" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
  <circle cx="30" cy="30" r="14" fill="rgba(255,255,255,0.9)"/>
</svg>
```

### 标注数据格式

```js
annotations: [
  {
    id: 'ann-1',
    targetFloor: 'floor-1',
    position: [x, y],        // 地图上的坐标
    label: '1F 大厅',        // 显示文字（可选）
  },
]
```

### 技术选型

- **Leaflet** — 地图 + tile layer 管理 + flyTo 动画
- **SVG overlay** — 引出线（L.svgOverlay 或自定义 pane）
- **Vue** — 楼层切换器组件 + 状态管理

### 右侧楼层切换器

```
┌──────────┐
│  7F 放映厅 │
│  6F       │
│  5F       │
│  4F       │
│  3F       │
│  2F 儿童区 │
│  1F 大厅   │
│  ─────── │
│  整体外观  │
└──────────┘
```

当前楼层高亮，点击切换（楼层间垂直滑动，进/出整体缩放动画）。

## 待讨论

- [x] 图标样式 — SVG 水滴形，已创建 7 个 SVG 文件
- [x] 颜色系统 — 7 色映射 SVG
- [x] 编辑器 UI 改造 — 已有改造计划
- [x] 多楼层架构 — 引出线 + SVG 标点 + 缩放动画
- [ ] 引出线样式细节（线宽、颜色、文字样式）
- [ ] 抽屉布局：缩放时抽屉行为
- [ ] 编辑器是否需要支持引出线编辑
