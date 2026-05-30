# zvp5-ocr 代码审查报告 & zvp5 对接方案

> 审查人：小鱼 🐟 | 日期：2026-05-30

---

## 一、代码审查 — ocr_api.py

### 🔴 严重问题 (Bugs)

| # | 位置 | 问题 | 严重性 |
|:---|:---|:---|:---|
| 1 | `upload_and_ocr()` L106-L108 | **文件大小读取后 seek(0) 无效**——`contents` 已被完整读取到内存，`file` 是 `UploadFile` Streaming 机制，`seek(0)` 后 **不会** 重新读到 `contents`。下面 `Image.open(io.BytesIO(contents))` 实际用的是同一个 `contents`，所以功能没问题但 **seek 是无效代码**，可能误导维护者 | 低 |
| 2 | `batch-upload` L139 | **批量接口缺少文件大小校验**——单文件有 10MB 检查，但批量接口没有，可被滥用来上传大文件 | 中 |
| 3 | `batch-upload` L144 | **批量接口缺少 detailed 参数**——单文件有 `detailed` 控制输出，批量接口直接返回带 `detailed_data` 的完整结果，无法精简 | 低 |
| 4 | `OCRProcessor.extract_text()` L52 | **未做超时控制**——`OCRConfig.timeout=30` 定义了但从未使用。大图/复杂场景下 `pytesseract` 可能卡住几十秒甚至分钟，会阻塞整个 uvicorn worker | 高 |
| 5 | `extract_text()` L66 整数化置信度 | **`int(data['conf'][i])` 可能抛 ValueError**——如果 tesseract 返回非数字的 conf 值（如空字符串），直接 int()会崩溃 | 中 |

### 🟡 设计问题

| # | 位置 | 问题 | 建议 |
|:---|:---|:---|:---|
| 6 | CORS `allow_origins=["*"]` | 生产环境允许所有来源不安全 | 改为 zvp5 前端域名白名单 |
| 7 | 无认证机制 | 任何人可调用 OCR 接口 | 加入 API Key 或与 zvp5 共享 JWT 验证 |
| 8 | `BackgroundTasks` 参数导入了但未使用 | 死代码过多 | 清理 |
| 9 | `tempfile` 导入了但未使用 | 死代码 | 清理 |
| 10 | 无请求限流 | 恶意用户可刷接口 | 加入 slowapi 或 nginx 限流 |
| 11 | 图片模式转换只处理了 3 种 | CMYK、I;16 等模式未处理 | 补全 `if image.mode not in ('RGB', 'L')` |
| 12 | `uvicorn.run(reload=True)` | 生产环境不应开 reload | 启动脚本中去掉 |

### 🟢 做得好的地方

- FastAPI 选择正确，自带 OpenAPI 文档
- 语言参数可配置（chi_sim+eng）
- 支持批量上传
- 有详细的置信度和 bbox 信息
- 健康检查接口包含 tesseract 可用性验证

---

## 二、zvp5 项目分析

zvp5 是镇海中学义工管理平台 v5，基于 FastAPI + SQLAlchemy + Pydantic，架构：
- `routers/v1/` — RESTful API（activities/users/platform）
- `models/` — SQLAlchemy ORM（Resource 模型管理文件资源）
- `schemas.py` — Pydantic 请求/响应模型
- `serializer.py` — 统一序列化
- `tasking.py` — 异步任务 + WebSocket 推送
- `crypto.py` — JWT 认证

**关键发现**：zvp5 的 `Resource` 模型存储文件元数据（object_id, name, size, url），义工活动通过 `ActivityResTable` 关联附件。这意味着 OCR 服务的图片来源是已上传到 zvp5 的 Resource URL。

---

## 三、zvp5 ↔ OCR 对接方案

### 架构设计

```
zvp5 前端/后端  ──→  OCR API (zvp5-ocr)
   │                      │
   │  1. 上传图片到 OCR    │
   │  2. OCR 返回文本结果  │
   │  3. 可选：保存结果回   │
   │     zvp5 Resource    │
```

### 请求格式

#### 接口1：单图 OCR（核心）

```
POST /upload
Content-Type: multipart/form-data

参数:
  file:       <binary>     必填，图片文件
  language:   "chi_sim+eng" 可选，OCR语言（默认中英混合）
  detailed:   "true"/"false" 可选，是否返回详细bbox信息（默认false）
```

#### 接口2：批量 OCR

```
POST /batch-upload
Content-Type: multipart/form-data

参数:
  files:      <binary[]>   必填，图片文件列表（≤10个）
  language:   "chi_sim+eng" 可选
```

#### 接口3：URL 方式（建议新增）

zvp5 的附件已有 URL，建议 OCR 服务新增此接口，避免前端重复上传：

```
POST /ocr-by-url
Content-Type: application/json

{
  "url": "https://resource.zvp5.example.com/xxx.png",
  "language": "chi_sim+eng",
  "detailed": false
}
```

### 响应格式

#### 成功响应 — 简洁模式 (detailed=false)

```json
{
  "success": true,
  "text": "识别出的文字内容",
  "word_count": 42,
  "processing_time": 1.23,
  "average_confidence": 87.5
}
```

#### 成功响应 — 详细模式 (detailed=true)

```json
{
  "success": true,
  "text": "识别出的文字内容",
  "word_count": 42,
  "processing_time": 1.23,
  "average_confidence": 87.5,
  "detailed_data": {
    "boxes": 56,
    "words_with_confidence": [
      {
        "text": "镇海",
        "confidence": 95,
        "bbox": { "x": 120, "y": 45, "width": 60, "height": 28 }
      },
      {
        "text": "中学",
        "confidence": 92,
        "bbox": { "x": 185, "y": 45, "width": 55, "height": 28 }
      }
    ]
  }
}
```

#### 错误响应

```json
{
  "success": false,
  "error": "UnsupportedImageFormat",
  "message": "不支持的文件格式。支持的格式: .jpg, .jpeg, .png, .bmp, .tiff, .webp"
}
```

#### 批量响应

```json
{
  "results": [
    {
      "filename": "img1.png",
      "success": true,
      "text": "...",
      "word_count": 10,
      "processing_time": 0.8,
      "average_confidence": 90.2
    },
    {
      "filename": "img2.jpg",
      "success": false,
      "error": "不支持的文件格式"
    }
  ]
}
```

### zvp5 侧集成代码示例

```python
# 在 zvp5 的 routers/v1/ 下新增 ocr.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
from ... import config

router = APIRouter(prefix='/ocr')

OCR_BASE = getattr(config, 'OCR_SERVICE_URL', 'http://ocr:8000')

class OcrRequest(BaseModel):
    resource_id: str          # zvp5 Resource.object_id
    language: str = 'chi_sim+eng'
    detailed: bool = False

class OcrResponse(BaseModel):
    success: bool
    text: str
    word_count: int
    processing_time: float
    average_confidence: float

@router.post('/recognize', response_model=OcrResponse)
async def recognize_text(req: OcrRequest, token: Token = Depends(crypto.token)):
    """从已有的Resource URL获取图片，调用OCR服务"""
    # 1. 从 zvp5 DB 获取 Resource URL
    async with db.session() as session:
        resource = await session.scalar_one(
            db.select(Resource).where(Resource.object_id == req.resource_id)
        )
    
    # 2. 调用 OCR 服务的 /ocr-by-url 接口
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f'{OCR_BASE}/ocr-by-url', json={
            'url': resource.url,
            'language': req.language,
            'detailed': req.detailed,
        })
    
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail='OCR服务异常')
    
    return resp.json()
```

### 部署建议

| 项目 | 建议 |
|:---|:---|
| 部署方式 | Docker Compose，OCR 服务与 zvp5 在同一网络 |
| 域名 | `ocr.zvp5.internal`（内网）或 `ocr.zhzx.dev`（公网） |
| 认证 | 先用 API Key（Header: `X-OCR-Key`），后续可改 JWT |
| 限流 | nginx 层 `limit_req` 或 slowapi 10 req/min |
| 超时 | OCR 请求设 30s 超时，zvp5 的 httpx 设 35s |

---

## 四、OCR 服务建议修复优先级

1. **🔴 加入 OCR 超时控制**（防止 worker 阻塞）
2. **🟡 新增 /ocr-by-url 接口**（zvp5 对接刚需）
3. **🟡 加入 API Key 认证**
4. **🟡 修复 batch-upload 缺少大小校验**
5. **🟢 清理死代码（unused imports）**
6. **🟢 生产环境关闭 reload**
