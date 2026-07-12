# Pannellum 2.5.7 参考文档

来源: https://pannellum.org/documentation/ + 源码分析

---

## 1. 概述

Pannellum 基于 WebGL + JavaScript 构建，支持三种全景图格式：

| 格式 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| `equirectangular` | 等距柱状投影（单张图） | 最简单，自动读取 Photo Sphere XMP | 最大建议 4096px 宽 |
| `cubemap` | 立方体贴图（6 张面图） | 支持更高分辨率（每面最大 4096px），支持 CSS 3D 回退 | 需要 6 张图 |
| `multires` | 多分辨率切片（切片金字塔） | 支持任意大小图片，加载快 | 需要预处理，文件数量多 |

**部署方式：** 静态文件，可放在任何 Web 服务器上。也提供 CDN。

---

## 2. 配置参数

### 2.1 通用参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | `"equirectangular"` | 全景图类型：`equirectangular`、`cubemap`、`multires` |
| `title` | string | - | 全景图标题 |
| `author` | string | - | 作者名 |
| `authorURL` | string | - | 作者链接（需配合 `author`） |
| `strings` | dict | - | 自定义/翻译界面文字 |
| `basePath` | string | - | 图片基础路径 |
| `autoLoad` | boolean | `false` | 自动加载全景图 |
| `autoRotate` | number | - | 自动旋转速度（度/秒），正值逆时针，负值顺时针 |
| `autoRotateInactivityDelay` | number | - | 用户停止操作后延迟多少毫秒开始自动旋转 |
| `autoRotateStopDelay` | number | - | 加载后延迟多少毫秒停止自动旋转 |
| `fallback` | string | - | 不支持 Pannellum 时的回退 URL |
| `orientationOnByDefault` | boolean | `false` | 启用设备方向控制 |
| `showZoomCtrl` | boolean | `true` | 显示缩放控件 |
| `keyboardZoom` | boolean | `true` | 允许键盘缩放 |
| `mouseZoom` | boolean/string | `true` | 鼠标滚轮缩放，可设为 `"fullscreenonly"` |
| `draggable` | boolean | `true` | 允许鼠标/触摸拖拽 |
| `friction` | number | `0.15` | 拖拽惯性摩擦力 (0.0, 1.0] |
| `disableKeyboardCtrl` | boolean | `false` | 禁用键盘控制 |
| `showFullscreenCtrl` | boolean | `true` | 显示全屏按钮 |
| `showControls` | boolean | `true` | 显示所有控件 |
| `touchPanSpeedCoeffFactor` | number | `1` | 触摸平移速度系数 |
| `yaw` | number | `0` | 初始偏航角（度） |
| `pitch` | number | `0` | 初始俯仰角（度） |
| `hfov` | number | `100` | 初始水平视场角（度） |
| `minYaw` / `maxYaw` | number | `-180` / `180` | 偏航角范围限制 |
| `minPitch` / `maxPitch` | number | `undefined` | 俯仰角范围限制（默认 -90/90） |
| `minHfov` / `maxHfov` | number | `50` / `120` | 视场角范围限制 |
| `multiResMinHfov` | boolean | `false` | multires 模式下是否忽略 minHfov |
| `compass` | boolean | `false` | 显示指南针（有 Photo Sphere XMP 时默认 `true`） |
| `northOffset` | number | - | 全景图中心相对正北的偏移角度（影响指南针） |
| `preview` | string | - | 加载前的预览图 URL |
| `previewTitle` | string | - | 加载按钮显示的标题 |
| `previewAuthor` | string | - | 加载按钮显示的作者 |
| `horizonPitch` | number | - | 图像地平线俯仰角（度），用于校正非水平全景图 |
| `horizonRoll` | number | - | 图像地平线翻滚角（度） |
| `escapeHTML` | boolean | `false` | 转义配置中的 HTML（独立查看器默认 `true`） |
| `crossOrigin` | string | `"anonymous"` | CORS 请求类型 |
| `backgroundColor` | [number,number,number] | `[0,0,0]` | 背景色 RGB [0,1] |
| `avoidShowingBackground` | boolean | `false` | 防止显示局部全景图的越界区域 |
| `hotSpotDebug` | boolean | `false` | 点击时记录 pitch/yaw 到控制台（调试用） |
| `sceneFadeDuration` | number | - | 场景切换淡入淡出时长（毫秒） |
| `capturedKeyNumbers` | array | - | 捕获的按键编号 |
| `animationTimingFunction` | function | `easeInOutQuad` | 动画时间函数（仅 API） |

### 2.2 Equirectangular 专用参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `panorama` | string | - | 全景图 URL（相对于 basePath） |
| `haov` | number | `360` | 水平视角范围（度），用于非 360° 全景 |
| `vaov` | number | `180` | 垂直视角范围（度），用于非 180° 全景 |
| `vOffset` | number | `0` | 等距柱状图中心相对地平线的垂直偏移（度） |
| `ignoreGPanoXMP` | boolean | `false` | 忽略 Photo Sphere XMP 数据 |

### 2.3 Cubemap 专用参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `cubeMap` | array | 6 张面图 URL，顺序：前、右、后、左、上、下。可设 `null` 表示缺失面 |

### 2.4 Multires 专用参数

```javascript
{
    type: 'multires',
    multiRes: {
        basePath: 'tiles/scene1',        // 切片基础路径
        path: '/%s/%l/%y/%x',           // 路径模板
        fallbackPath: '/fallback/%s',    // CSS 3D 回退面图路径
        extension: 'jpg',                // 文件扩展名（不含 .）
        tileResolution: 512,             // 单个切片分辨率（像素）
        maxLevel: 2,                     // 最大缩放级别
        cubeResolution: 2560             // 立方体面原始分辨率（像素）
    }
}
```

**路径模板占位符：**
- `%l` — 缩放级别
- `%s` — 面名称（f, r, b, l, u, d）
- `%x` — x 索引（列）
- `%y` — y 索引（行）

**maxLevel 计算：** `Math.ceil(Math.log2(cubeResolution / tileResolution))`

### 2.5 热点配置

```javascript
hotSpots: [
    {
        pitch: 0,           // 俯仰角（度）
        yaw: 90,            // 偏航角（度）
        type: 'scene',      // 'scene' 或 'info'
        text: '提示文字',    // 悬停显示文字
        sceneId: 'scene2',  // scene 类型：目标场景 ID
        URL: 'https://...', // info 类型：链接 URL
        targetPitch: 0,     // 目标场景俯仰角（可设 'same'）
        targetYaw: 0,       // 目标场景偏航角（可设 'same' / 'sameAzimuth'）
        targetHfov: 100,    // 目标场景视场角（可设 'same'）
        cssClass: 'my-class',
        scale: false,       // 是否随视场角缩放
        id: 'hotspot1',     // 热点 ID（用于 API 删除）
        attributes: {},     // 链接属性
        createTooltipFunc: (el) => { el.innerHTML = 'HTML'; },
        createTooltipArgs: {},
        clickHandlerFunc: (event, args) => {},
        clickHandlerArgs: {}
    }
]
```

### 2.6 Tour 配置文件结构

```javascript
{
    default: {
        firstScene: 'scene1',  // 必须！首个场景 ID
        // ... 其他默认参数
    },
    scenes: {
        scene1: { /* 场景配置 */ },
        scene2: { /* 场景配置 */ }
    }
}
```

---

## 3. API

### 3.1 创建查看器

```javascript
const viewer = pannellum.viewer('containerId', {
    // 配置参数
});
```

### 3.2 Viewer 方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `isLoaded()` | - | boolean | 检查全景图是否已加载 |
| `getPitch()` | - | number | 获取当前俯仰角（度） |
| `setPitch(pitch, animated, callback, callbackArgs)` | pitch: number, animated?: boolean\|number | Viewer | 设置俯仰角 |
| `getPitchBounds()` | - | [number, number] | 获取俯仰角范围 |
| `setPitchBounds(bounds)` | [min, max] | Viewer | 设置俯仰角范围 |
| `getYaw()` | - | number | 获取当前偏航角（度） |
| `setYaw(yaw, animated, callback, callbackArgs)` | yaw: number, animated?: boolean\|number | Viewer | 设置偏航角 [-180, 180] |
| `getYawBounds()` | - | [number, number] | 获取偏航角范围 |
| `setYawBounds(bounds)` | [min, max] | Viewer | 设置偏航角范围 [-180, 180] |
| `getHfov()` | - | number | 获取当前水平视场角（度） |
| `setHfov(hfov, animated, callback, callbackArgs)` | hfov: number, animated?: boolean\|number | Viewer | 设置水平视场角 |
| `getHfovBounds()` | - | [number, number] | 获取视场角范围 |
| `setHfovBounds(bounds)` | [min, max] | Viewer | 设置视场角范围 |
| `lookAt(pitch, yaw, hfov, animated, callback, callbackArgs)` | 全部可选 | Viewer | 设置新视角（未指定的参数不变） |
| `getNorthOffset()` | - | number | 获取正北偏移（度） |
| `setNorthOffset(heading)` | number | Viewer | 设置正北偏移 |
| `getHorizonRoll()` | - | number | 获取地平线翻滚角（度） |
| `setHorizonRoll(roll)` | number [-90,90] | Viewer | 设置地平线翻滚角 |
| `getHorizonPitch()` | - | number | 获取地平线俯仰角（度） |
| `setHorizonPitch(pitch)` | number [-90,90] | Viewer | 设置地平线俯仰角 |
| `startAutoRotate(speed?, pitch?)` | speed?: number, pitch?: number | Viewer | 开始自动旋转 |
| `stopAutoRotate()` | - | Viewer | 停止自动旋转 |
| `stopMovement()` | - | - | 停止所有运动 |
| `getRenderer()` | - | Renderer | 获取渲染器实例 |
| `setUpdate(bool)` | boolean | Viewer | 设置动态内容更新标志 |
| `mouseEventToCoords(event)` | MouseEvent | [pitch, yaw] | 将鼠标事件转换为全景坐标 |
| `loadScene(sceneId, pitch?, yaw?, hfov?)` | sceneId: string | Viewer | 切换场景 |
| `getScene()` | - | string | 获取当前场景 ID |
| `addScene(sceneId, config)` | sceneId: string, config: object | Viewer | 添加新场景 |
| `removeScene(sceneId)` | sceneId: string | boolean | 删除场景（当前场景或不存在时返回 false） |
| `toggleFullscreen()` | - | Viewer | 切换全屏 |
| `getConfig()` | - | object | 获取当前场景配置 |
| `getContainer()` | - | HTMLElement | 获取容器元素 |
| `addHotSpot(hs, sceneId?)` | hs: object, sceneId?: string | Viewer | 添加热点 |
| `removeHotSpot(hotSpotId, sceneId?)` | hotSpotId: string, sceneId?: string | boolean | 删除热点 |
| `resize()` | - | - | 容器大小变化后调用 |
| `isOrientationSupported()` | - | boolean | 检查是否支持设备方向 |
| `stopOrientation()` | - | - | 停止设备方向控制 |
| `startOrientation()` | - | - | 启动设备方向控制 |
| `isOrientationActive()` | - | boolean | 检查设备方向是否激活 |
| `on(type, listener)` | type: string, listener: Function | Viewer | 订阅事件 |
| `off(type?, listener?)` | type?: string, listener?: Function | Viewer | 取消订阅事件 |
| `destroy()` | - | - | 销毁查看器 |

### 3.3 事件

| 事件名 | 说明 | 回调参数 |
|--------|------|----------|
| `load` | 全景图加载完成 | - |
| `scenechange` | 场景切换开始 | sceneId (string) |
| `fullscreenchange` | 全屏状态变化 | status (boolean) |
| `zoomchange` | 视场角变化 | hfov (number) |
| `scenechangefadedone` | 场景切换淡入淡出完成 | - |
| `animatefinished` | 动画/运动完成 | [pitch, yaw, hfov] |
| `error` | 发生错误 | errorMessage (string) |
| `errorcleared` | 错误已清除 | - |
| `mousedown` | 鼠标按下 | MouseEvent |
| `mouseup` | 鼠标释放 | MouseEvent |
| `touchstart` | 触摸开始 | TouchEvent |
| `touchend` | 触摸结束 | TouchEvent |

### 3.4 Renderer 方法（底层）

| 方法 | 说明 |
|------|------|
| `init(_image, _imageType, _dynamic, haov, vaov, voffset, callback, params?)` | 初始化渲染器 |
| `destroy()` | 销毁渲染器 |
| `resize()` | 调整大小 |
| `setPose(horizonPitch, horizonRoll)` | 设置地平线姿态 |
| `render(pitch, yaw, hfov, params?)` | 渲染新视角（参数为弧度） |
| `isLoading()` | 检查是否正在加载 |
| `getCanvas()` | 获取 canvas 元素 |

---

## 4. Cubemap 面顺序

Pannellum 源码中的面定义：

```javascript
// libpannellum.js 中的顶点定义
var sides = ['f', 'b', 'u', 'd', 'l', 'r'];

// 顶点数据（4角 × 3坐标 = 12 floats/面）
var vertices = [
    // f (前): (-1,1,-1), (1,1,-1), (-1,-1,-1), (1,-1,-1)  → 法线 -Z
    // b (后): (1,1,1), (-1,1,1), (1,-1,1), (-1,-1,1)      → 法线 +Z
    // u (上): (-1,1,1), (1,1,1), (-1,1,-1), (1,1,-1)      → 法线 +Y
    // d (下): (-1,-1,-1), (1,-1,-1), (-1,-1,1), (1,-1,1)  → 法线 -Y
    // l (左): (-1,1,1), (-1,1,-1), (-1,-1,1), (-1,-1,-1)  → 法线 -X
    // r (右): (1,1,-1), (1,1,1), (1,-1,-1), (1,-1,1)      → 法线 +X
];
```

### 等距柱状投影 → 立方体面坐标映射

```
theta = atan2(dx, dz)     // 水平方位角 [-π, π]
phi = arcsin(dy)           // 垂直仰角 [-π/2, π/2]

eq_x = (theta/π + 1) * 0.5 * (w-1)   // 映射到图片 x 像素
eq_y = (0.5 - phi/π) * (h-1)          // 映射到图片 y 像素
```

### 各面方向映射（Python 用）

```python
# u, v ∈ [-1, 1]，面内归一化坐标
f: dx=u,  dy=v,  dz=-1     # 前: 法线 -Z
r: dx=1,  dy=v,  dz=u      # 右: 法线 +X
b: dx=-u, dy=v,  dz=1      # 后: 法线 +Z
l: dx=-1, dy=v,  dz=-u     # 左: 法线 -X
u: dx=u,  dy=1,  dz=v      # 上: 法线 +Y
d: dx=u,  dy=-1, dz=-v     # 下: 法线 -Y
```

---

## 5. 常见问题

- `firstScene` 必须设置，否则不会创建 canvas
- `load` 事件在 multires 模式下可能不触发，需 `setTimeout` 兜底
- `horizonPitch` 用于校正地平线偏移，一般 ±10° 以内
- 切片文件路径必须与 `path` 模板匹配
- `maxLevel` 和 `cubeResolution` 必须与实际切片一致
- `minHfov` 在 multires 模式下默认被忽略（需设 `multiResMinHfov: true` 才生效）
- `cubeMap` 面顺序为：前、右、后、左、上、下
- 热点调试：设 `hotSpotDebug: true` 可在控制台看到点击位置的 pitch/yaw

---

## 6. 官方切片生成工具

Pannellum 官方提供 `utils/multires/generate.py`，依赖 Hugin 的 `nona` 工具。

```bash
python generate.py -f 512 -o output/ panorama.jpg
```

官方路径模板：`"/%l/%s%y_%x"` → `/level/faceRow_Col.jpg`（扁平结构）

我们项目的自定义脚本 `generate_tiles.py` 使用目录结构：`/{face}/{level}/{row}/{col}.jpg`
