# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**云游闽图** — 闽图（福建省图书馆）建筑可视化平台，由三个独立子项目组成。三个服务协同工作：切片服务生成瓦片 → 前端消费瓦片展示地图 → 360° 全景提供沉浸导览。

## 子项目一览

| 目录 | 定位 | 技术栈 | 端口 |
|------|------|--------|------|
| `makeTiles/` | 瓦片切片服务（后端） | Python 3.12 + FastAPI + GDAL | 8000 |
| `mintuMap/` | 楼层地图前端 | Vue 3.5 + Vite + Leaflet + Tailwind | 3001 (dev) |
| `360camera/` | 360° 全景导览 | Vanilla JS + Pannellum 2.5.7 | 3000 |

## 各子项目快速启动

### makeTiles — 切片服务
```bash
conda activate maketiles
python run.py
# → http://localhost:8000/admin/
```

### mintuMap — 楼层地图前端
```bash
cd mintuMap
pnpm install
pnpm dev
# → http://localhost:3001
```
- `/` — 只读展示页面（多楼层 Viewer）
- `/editor` — 标点/标注编辑器

### 360camera — 全景导览
```bash
cd 360camera
npm start
# → http://localhost:3000
```

## mintuMap 架构

### 数据流（生产环境）

```
makeTiles 切片 → mintuMap/data/tiles/{uuid}/ → 复制到 public/tiles/{floor-name}/
                                                    ↓
src/data/tiles/{floor-name}/manifest.json  ← manifest JSON（import 用）
public/tiles/{floor-name}/{z}/{x}/{y}.png  ← 瓦片图片（URL 访问）
                                                    ↓
src/data/floors.js  → import 所有 manifest → export FLOOR_CONFIG
                                                    ↓
TileImageViewer1-fixed.vue  → import FLOOR_CONFIG → 构建地图（零 fetch）
```

### 关键文件

| 文件 | 职责 |
|------|------|
| `src/data/floors.js` | 硬编码楼层配置（import 9 个 manifest JSON + viewMinZoom/viewMaxZoom） |
| `src/data/tiles/*/manifest.json` | 每层楼的 manifest（尺寸、zoom、urlTemplate） |
| `public/tiles/*/` | 瓦片图片文件（通过 URL 访问） |
| `public/pin_*.svg` | 7 种标点 SVG 图标 |
| `src/components/TileImageViewer1-fixed.vue` | 多楼层只读 Viewer |
| `src/components/MarkerEditor1.vue` | 标点/标注编辑器 |
| `src/views/show.vue` | 展示路由 `/` |
| `src/views/editor.vue` | 编辑路由 `/editor` |

### 多楼层系统

所有楼层统一为 16384×16384 像素（透明填充，只缩小不放大），坐标系完全一致。

Viewer 管理 9 个楼层，每个楼层有独立的：
- `ExactTileLayer`（Leaflet 瓦片图层，bounds 基于 16384×16384）
- Marker LayerGroup（标点）
- Annotation LayerGroup（标注，双圈白色圆形标记）

楼层切换动画：
- 移除旧图层 → `fitBounds` 到目标楼层 → 淡入新图层
- 所有楼层尺寸一致，坐标系相同，切换无跳动

每个楼层有 `viewMinZoom` / `viewMaxZoom` 控制缩放范围：
- 整体外观：0.5-5
- 各楼层：1.25-5
- 7F 放映厅：1.25-3.5

### 标点数据格式

```js
// 楼层内部标点
{ id, position: [x, y], title, color, label: [], text, type }

// 整体外观标注（入口标记）
{ id, position: [x, y], label, targetFloor }
```

颜色映射（自动关联 SVG）：
| color | SVG 文件 | 用途 |
|-------|---------|------|
| `blue` | `pin_blue.svg` | 通用建筑 |
| `blueDark` | `pin_blueDark.svg` | 重要建筑 |
| `gray` | `pin_gray.svg` | 宿舍/附属 |
| `red` | `pin_red.svg` | 服务设施 |
| `orange` | `pin_orange.svg` | 餐厅 |
| `gate` | `pin_gate.svg` | 入口/门 |
| `landmark` | `pin_landmark.svg` | 地标 |

### 编辑器工作流

1. 编辑器从 makeTiles API 获取 manifest（需启动 makeTiles）
2. 添加标点/标注，编辑属性，导出 JSON
3. 将导出的 JSON 手动合并到 `src/data/floors.js`
4. 构建后瓦片和数据打包在一起，无需后端服务

### manifest 字段

```json
{
  "id": "floor-1-lobby",
  "width": 16384, "height": 16384,
  "minZoom": 0, "maxZoom": 5,
  "tileSize": 512,
  "urlTemplate": "/tiles/floor-1-lobby/{z}/{x}/{y}.png",
  "imageExtension": "png"
}
```

`urlTemplate` 使用相对路径，瓦片从 `public/tiles/` 静态服务。

## makeTiles 架构

- **核心文件**：`main.py`（路由+任务管理）、`tile_engine.py`（GDAL 切片逻辑）、`settings.py`（热加载配置）
- 通过 `gdal2tiles` 将大图切为金字塔瓦片，自动根据图片尺寸选择 tile size（256/512/1024/2048）
- `process_image_bytes` 中调用 `unify_image_size` 将所有图片 resize+padding 到 16384×16384（透明填充，只缩小不放大）
- 异步任务模型：POST 创建任务 → 202 返回 jobId → 轮询 jobId 获取结果
- 产物存放在 `app/data/` 下：images、tiles、manifests、thumbs
- 详细 API 见 `makeTiles/CLAUDE.md`

### 批量切片脚本

- `makeTiles/unify_images.py` — 将 images/ 中的图片统一 resize+padding 到 16384×16384（透明填充）
- `makeTiles/batch_cut.py` — 批量切片，读取 images_unified/ 输出到 app/data/tiles/
- 运行：`conda activate maketiles && python batch_cut.py`
- 切片完成后复制瓦片到 mintuMap：`cp -r app/data/tiles/* ../heryin-云游闵图/mintuMap/public/tiles/`

## 360camera 架构

- 两种查看模式：multires（预生成立方体贴图瓦片）和 equirectangular（直接加载全景图）
- 瓦片生成需要 Hugin 的 `nona`
- 详细说明见 `360camera/CLAUDE.md`

## 关键约定

- **语言**：UI 和注释均使用中文
- **瓦片坐标系**：makeTiles 使用 XYZ 方案（`--xyz`），Y 轴向下
- **Leaflet CRS**：前端使用 `L.CRS.Simple`（像素坐标系），不是经纬度
- **生产环境零 fetch**：Viewer 通过 import 加载 manifest，不依赖后端 API
- **CORS**：makeTiles 默认允许所有来源（`["*"]`）
