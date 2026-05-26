# OCR API Server

基于 pytesseract + FastAPI 的图片文字识别 API 服务

## 功能特性

- 📝 支持多种图片格式（JPG, PNG, BMP, TIFF, WEBP）
- 🌏 支持中英文混合识别
- 📊 返回详细的OCR识别结果和置信度
- 🚀 支持批量处理多个图片
- 🔧 RESTful API 设计
- 📖 自动生成API文档

## 环境要求

### 系统依赖
```bash
# 安装 Tesseract OCR 引擎
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra
```

### Python 依赖
```bash
fastapi==0.104.1
uvicorn[standard]==0.24.0
pytesseract==0.3.10
Pillow==10.1.0
python-multipart==0.0.6
```

## 快速开始

### 1. 启动服务
```bash
cd ~/.openclaw/workspace
./start_ocr_api.sh
```

### 2. 访问服务
- API 地址: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## API 使用说明

### 单图片OCR识别

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@test.jpg" \
  -F "language=chi_sim+eng" \
  -F "detailed=true"
```

#### 请求参数
- `file`: 图片文件（必需）
- `language`: OCR语言，默认 `chi_sim+eng`（中文+英文）
- `detailed`: 是否返回详细数据，默认 `false`

#### 响应格式
```json
{
  "success": true,
  "text": "识别出的文字内容",
  "word_count": 10,
  "processing_time": 2.5,
  "average_confidence": 95.2,
  "detailed_data": {
    "boxes": 5,
    "words_with_confidence": [
      {
        "text": "你好",
        "confidence": 98,
        "bbox": {
          "x": 10,
          "y": 20,
          "width": 50,
          "height": 30
        }
      }
    ]
  }
}
```

### 批量图片OCR识别

```bash
curl -X POST "http://localhost:8000/batch-upload" \
  -F "files=@test1.jpg" \
  -F "files=@test2.png" \
  -F "language=chi_sim+eng"
```

#### 响应格式
```json
{
  "results": [
    {
      "filename": "test1.jpg",
      "success": true,
      "text": "第一个图片的文字",
      "word_count": 5,
      "processing_time": 1.2,
      "average_confidence": 92.1
    },
    {
      "filename": "test2.png",
      "success": true,
      "text": "第二个图片的文字",
      "word_count": 8,
      "processing_time": 1.8,
      "average_confidence": 88.5
    }
  ]
}
```

## 支持的图片格式

- JPG/JPEG
- PNG
- BMP
- TIFF
- WEBP

## 支持的语言

- `chi_sim`: 简体中文
- `chi_tra`: 繁体中文
- `eng`: 英文
- `chi_sim+eng`: 中英文混合（默认）

## 错误处理

API 会返回适当的 HTTP 状态码和错误信息：

- `400`: 请求参数错误（不支持的文件格式、文件过大等）
- `500`: 服务器内部错误

## 性能限制

- 单个文件最大: 10MB
- 批量处理最多: 10个文件
- 处理超时: 30秒

## 开发说明

### 项目结构
```
~/.openclaw/workspace/
├── ocr_api.py          # 主应用文件
├── requirements.txt    # Python依赖
├── start_ocr_api.sh    # 启动脚本
└── README.md          # 说明文档
```

### 自定义配置

可以修改 `ocr_api.py` 中的 `OCRConfig` 类来调整：
- 支持的文件格式
- 文件大小限制
- 处理超时时间

## 故障排除

### 1. Tesseract 未安装
```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra
```

### 2. 依赖包问题
```bash
cd ~/.openclaw/workspace
source ocr_env/bin/activate
pip install -r requirements.txt
```

### 3. 端口占用
修改 `ocr_api.py` 中的端口号，或使用以下命令启动：
```bash
source ocr_env/bin/activate
python ocr_api.py --host 0.0.0.0 --port 8001
```