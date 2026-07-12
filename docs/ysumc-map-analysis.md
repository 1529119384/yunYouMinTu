# ysumc.net/map.html 页面分析

燕山大学 Minecraft 学生同好者协会的校园复原导览地图，基于 Vue 3 + Leaflet + Tailwind CSS 构建。

## 技术栈

- **Vue 3**（`data-v-12083efd` 指令，`__vue_app__`）
- **Leaflet**（CRS.Simple 像素坐标系，瓦片格式 webp）
- **Tailwind CSS**（原子化类名）
- **数据独立文件**：`dataloader-9bCBnYbp.js` 导出标点数组

## 标点数据结构

每个标点是一个 JS 对象：

```js
{
  position: [x, y],        // 像素坐标 [列, 行]
  title: "标点名称",
  color: "blue",           // 颜色类型（决定标点和标签颜色）
  label: ["教学楼"],       // 分类标签（数组，显示在抽屉中）
  text: "描述文字",        // 支持 <br> HTML
  buildingType: "building" // 建筑类型标识
}
```

### buildingType 枚举

- `landmark` — 地标
- `building` — 建筑（学院、办公楼等）
- `gym` — 体育场馆
- `dorm` — 学生宿舍
- `gate` — 校门
- `canteen` — 餐厅
- `live` — 生活服务设施

## 颜色系统

共 6 种颜色，通过 SVG path fill + circle fill 组合实现：

| color 值 | path fill | circle fill | 用途 | 标签背景色 | 标点数量 |
|----------|-----------|-------------|------|-----------|---------|
| `blue` | 白色 `#fff` | 青色 `rgb(102,204,204)` | 学院/教学楼/体育馆 | 青色 | ~70 |
| `blueDark` | 白色 `#fff` | 深蓝 `rgb(31,41,106)` | 重要建筑/地标 | 深蓝 | ~6 |
| `gray` | 白色 `#fff` | 深灰 `rgb(59,59,59)` | 学生宿舍 | 深灰 | ~21 |
| `red` | 白色 `#fff` | 红色 `rgb(204,102,102)` | 服务设施/快递/浴池 | 红色 | ~6 |
| `orange` | 白色 `#fff` | 橙色 `rgb(211,104,57)` | 餐厅 | 橙色 | ~5 |
| `gate` | 深蓝全填充 `rgb(31,41,106)` | 深蓝全填充 | 校门 | 深蓝 | ~8 |

### 颜色映射规则

`color` 字段决定：
1. 标点 SVG 圆形（`circle.st1`）的 fill 颜色
2. 抽屉中分类标签（`<span>`）的 `background-color`
3. 选中状态时水滴外框（`path.st2`）是否变为全填充

## 标点 SVG 结构

```svg
<svg viewBox="0 0 104.6 144.9">
  <!-- 水滴外框 -->
  <path class="st2" fill="rgb(255,255,255)"
        d="M52.4,0C23.5,0,0,24.1,0,53.8s28,66,49.5,89.8..." />
  <!-- 彩色圆点 -->
  <circle class="st1" cx="52.4" cy="53.8" r="20"
          fill="rgb(102,204,204)" />
</svg>
```

### 标点状态

| 状态 | SVG transform | path fill | circle fill |
|------|--------------|-----------|-------------|
| 默认 | `scale(1)` | 白色 | 对应颜色 |
| 选中 | `scale(2)` | 对应颜色（全填充） | 对应颜色 |

## 交互行为

### 1. 点击标点

1. 标点 SVG 从 `scale(1)` 放大到 `scale(2)`
2. 水滴外框 path fill 从白色变为对应颜色（全填充）
3. 地图平移到标点位置（`flyTo` 或 `panTo`）
4. 底部抽屉动画切换为该标点信息

### 2. 点击空白区域

1. 所有标点恢复 `scale(1)`
2. 底部抽屉滑出隐藏（`translate-y-full`）

### 3. 侧边栏列表

- 左上角按钮切换侧边栏显示/隐藏
- 点击列表项等同于点击对应标点
- 列表包含所有 117 个标点名称

### 4. 缩放

- 滚轮缩放地图
- 标点大小不随缩放变化（固定像素大小）
- 抽屉在缩放时无变化

## 底部抽屉（Drawer）

### 定位与样式

```
position: fixed
bottom: 0
width: 100vw
z-index: 10000
background: rgba(255,255,255,0.9)  /* bg-white/90 */
backdrop-filter: blur()            /* backdrop-blur */
box-shadow: 0 25px 50px -12px      /* shadow-2xl */
```

### 三栏布局（桌面端 `md:flex-row`）

```
┌─────────────────────────────────────────────────────┐
│  左栏 (flex-1)        │  中栏 (hidden lg:flex)  │  右栏 │
│                        │                        │       │
│  h1 标题               │  [鼠标图标]             │ 描述   │
│  span 标签（彩色圆角）  │  按住左键拖动以移动     │ 文字   │
│                        │  [滚轮图标]             │       │
│                        │  鼠标滚轮可缩放大小     │       │
└─────────────────────────────────────────────────────┘
```

### 三种状态

#### 状态 1：初始/全局（无标点选中）

- 抽屉：`translate-y-0`（可见）
- 左栏：显示全局标题 + 说明段落，标签隐藏
- 中栏：`display: flex`，显示操作提示图标
- 右栏：`display: none`（隐藏）

```
标题：《像素燕大：燕山大学复原计划》全导览图（2024）
说明：本图按燕山大学2024年5月时的复原...
标签：（隐藏）
提示：按住左键拖动以移动 / 鼠标滚轮可缩放大小
描述：（隐藏）
```

#### 状态 2：选中标点

- 抽屉动画：`translate-y-full`(滑下) → 内容替换 → `translate-y-0`(滑入)
- 左栏：显示标点标题 + 分类标签（彩色背景）
- 中栏：`display: none`（隐藏操作提示）
- 右栏：`display: block`，显示详细描述

```
标题：燕山大学图书馆（西）
标签：图书馆（青色背景）
描述：2022年竣工，是燕山大学在新世纪下竣工的最大的建筑...
```

#### 状态 3：点击空白取消

- 抽屉：`translate-y-full`（滑出隐藏）
- 内容保留上次选中的标点信息

### 动画机制

```css
transition-transform ease-in-out duration-200
```

通过 Tailwind class 切换：
- `translate-y-full` → 抽屉滑出（y 方向 100%）
- `translate-y-0` → 抽屉滑入（y 方向 0）

切换标点时的完整流程：
1. 当前抽屉 `translate-y-full`（滑下，200ms）
2. Vue 响应式更新内容（标题、标签、描述替换）
3. 抽屉 `translate-y-0`（滑上，200ms）

### 标签样式

```html
<span class="inline-block text-white rounded px-3 md:px-4 py-1.5 md:py-2 font-bold text-sm md:text-base/loose"
      style="background-color: rgb(102, 204, 204);">
  图书馆
</span>
```

标签颜色与标点 `color` 字段对应，使用与 SVG circle 相同的 RGB 值。

## 页面结构

```
<body>
  <header>  <!-- 顶部导航栏 -->
  <main>
    <button>  <!-- 左上角侧边栏切换按钮（SVG 图标） -->
    <div>     <!-- 侧边栏列表（所有标点名称按钮） -->
    <div>     <!-- Leaflet 地图容器 -->
      <div class="leaflet-marker-pane">
        <!-- 117 个标点 SVG -->
      </div>
    </div>
    <div>     <!-- 底部抽屉 -->
  </main>
</body>
```

## 关键 CSS 类

- `.map-icon` — 标点容器
- `.leaflet-marker-icon` — Leaflet 标点默认类
- `.st0` — SVG group
- `.st1` — SVG circle（彩色圆点）
- `.st2` — SVG path（水滴外框）
- `font-ysumc` — 自定义字体（标题）

## 数据规模

- 总标点数：117 个
- 颜色分类：6 种
- 建筑类型：7 种
- 瓦片格式：webp
- 瓦片尺寸：512px
