# makeTiles — 图片切片服务

基于 FastAPI 的图片切片管理服务，支持 Web 管理界面。

## 功能

- 上传图片或传入 URL/本地路径，在线异步切片
- Web 管理界面：列表/画廊双模式、搜索、分页、备注、一键复制 ID、预览
- 自动生成 manifest（extent、resolutions、center、urlTemplate）
- Swagger API 文档（中文标注）
- 配置热加载（文件大小限制、CORS、缓存时间等）

## 安装

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

GDAL 需单独安装，确保 `python -m osgeo_utils.gdal2tiles` 可用。

## 启动

```bash
python run.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 访问

- 管理界面：http://localhost:8000/admin/
- API 文档：http://localhost:8000/docs

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tiles` | 创建切片任务 |
| GET | `/api/tiles` | 列出切片（分页+搜索） |
| GET | `/api/tiles/jobs/{id}` | 查询任务状态 |
| GET | `/api/tiles/{id}/manifest` | 获取 manifest |
| PATCH | `/api/tiles/{id}` | 更新备注 |
| DELETE | `/api/tiles/{id}` | 删除切片 |
| GET | `/api/tiles/{id}/{z}/{x}/{y}.png` | 获取瓦片 |
| GET | `/api/tiles/{id}/thumb` | 获取缩略图 |
| GET/PUT | `/api/config` | 配置管理（热加载） |

## 安全与限制

- SSRF 防护：远程 URL 解析到私有 IP 会被拒绝
- 文件大小限制：默认 200 MB（可通过 `/api/config` 修改）
- 子进程超时：gdal2tiles 默认 10 分钟
- CORS 可通过环境变量 `CORS_ORIGINS` 或配置接口修改
- 任务 1 小时后自动清理

## 生产建议

- 瓦片目录挂载到持久化存储
- 私有资源建议加鉴权
- 高并发场景建议瓦片放 CDN
