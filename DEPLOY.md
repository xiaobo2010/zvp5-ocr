# OCR API 部署指南

## 🚀 快速部署

### 1. 安装系统依赖
```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra
```

### 2. 启动服务
```bash
cd ~/.openclaw/workspace
./start_ocr_api.sh
```

### 3. 测试API
```bash
cd ~/.openclaw/workspace
source ocr_env/bin/activate
python test_api.py
```

## 📋 使用示例

### cURL 示例
```bash
# 单图片OCR
curl -X POST "http://localhost:8000/upload" \
  -F "file=@your_image.jpg" \
  -F "language=chi_sim+eng" \
  -F "detailed=true"

# 批量OCR
curl -X POST "http://localhost:8000/batch-upload" \
  -F "files=@image1.jpg" \
  -F "files=@image2.png" \
  -F "language=chi_sim+eng"
```

### Python 示例
```python
import requests

# 上传图片进行OCR
with open('test.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload',
        files={'file': f},
        data={'language': 'chi_sim+eng', 'detailed': 'true'}
    )
    
result = response.json()
print(result['text'])
```

## 🔧 服务管理

### 停止服务
按 `Ctrl+C` 停止OCR API服务

### 后台运行
```bash
nohup ./start_ocr_api.sh > ocr.log 2>&1 &
```

### 查看日志
```bash
tail -f ocr.log
```

## 🌐 访问地址

- **API根路径**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 📝 API 文档

访问 http://localhost:8000/docs 查看完整的Swagger API文档，包含：
- 所有端点的详细说明
- 请求/响应格式
- 参数说明
- 错误码说明

## 🔍 故障排除

### 常见问题

1. **Tesseract未安装**
   ```bash
   sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra
   ```

2. **端口被占用**
   修改 `ocr_api.py` 中的端口号，或使用：
   ```bash
   source ocr_env/bin/activate
   python ocr_api.py --host 0.0.0.0 --port 8001
   ```

3. **依赖包问题**
   ```bash
   cd ~/.openclaw/workspace
   source ocr_env/bin/activate
   pip install -r requirements.txt
   ```

### 日志查看
```bash
# 查看实时日志
tail -f ~/.openclaw/workspace/ocr.log

# 查看服务状态
ps aux | grep ocr_api.py
```

## 🎯 性能优化

### 提高识别速度
- 使用较小的图片尺寸
- 减少详细数据请求 (`detailed=false`)
- 选择合适的语言包

### 提高识别准确率
- 使用高质量的图片
- 启用详细模式 (`detailed=true`)
- 针对特定场景选择合适的语言组合

## 📊 监控指标

API 返回的性能指标：
- `processing_time`: 处理时间（秒）
- `word_count`: 识别出的单词数量
- `average_confidence`: 平均置信度（%）
- `detailed_data`: 详细的位置和置信度信息