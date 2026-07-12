# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 开发命令

```bash
pnpm install          # 安装依赖
pnpm dev              # 开发服务器 → http://127.0.0.1:3001
pnpm build            # 生产构建到 dist/
pnpm preview          # 预览构建产物
```

无测试、lint 或格式化工具配置。

## 架构概览

Vue 3.5 + Vite + Leaflet 1.9 + Tailwind CSS 4 的楼层地图前端。详细架构见上级目录 `../CLAUDE.md`。

### 路由

| 路径 | 组件 | 用途 |
|------|------|------|
| `/` | `src/views/show.vue` | 只读多楼层展示 |
| `/editor` | `src/views/editor.vue` | 标点/标注编辑器 |

### 核心文件

- `src/components/TileImageViewer1-fixed.vue` — 多楼层 Viewer，包含所有地图逻辑、楼层切换动画、标点渲染
- `src/components/MarkerEditor1.vue` — 编辑器组件
- `src/data/floors.js` — 楼层配置（import 9 个 manifest + 缩放限制 + 标点/标注数据）

### 关键技术点

- **Leaflet CRS.Simple**：像素坐标系，不是经纬度。`map.unproject([x, y], zoom)` 将像素坐标转为 Leaflet 内部坐标
- **所有楼层 16384×16384**：坐标系统一，切换无跳动
- **ExactTileLayer**：自定义 TileLayer 子类，基于 manifest 的 bounds 裁剪瓦片范围
- **生产环境零 fetch**：manifest 通过 ES import 静态加载，瓦片从 `public/tiles/` 访问

### 楼层切换动画

`slideTransition` 使用双 overlay 方案：
1. 克隆旧图层 DOM → `oldOverlay`（z-index: 10001）
2. 等待新图层瓦片加载（`waitForLayerReady`）
3. 克隆新图层 DOM → `newOverlay`（z-index: 10000）
4. CSS transition 同时：旧 overlay 滑出 + 新 overlay 滑入

**重要**：克隆 `.leaflet-tile-container` 时不能覆盖 `style.cssText`，必须保留 Leaflet 设置的 `transform: translate3d(x, y, 0) scale(s)`。只追加 `position: absolute; top: 0; left: 0`。

### 瓦片来源

开发时瓦片从 `public/tiles/` 静态目录加载。如需生成新瓦片：
1. 启动 makeTiles 服务（`conda activate maketiles && python run.py`）
2. 用编辑器 `/editor` 或 API 上传图片切片
3. 将 `makeTiles/app/data/tiles/` 中的产物复制到 `mintuMap/public/tiles/`
