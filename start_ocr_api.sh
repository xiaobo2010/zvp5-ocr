#!/bin/bash
# OCR API 启动脚本

# 设置工作目录
# cd ~/.openclaw/workspace

# 激活虚拟环境
source ocr_env/bin/activate

# 检查tesseract是否安装
if ! command -v tesseract &> /dev/null; then
    echo "错误：Tesseract OCR 未安装"
    echo "请先安装 tesseract-ocr 和中文语言包："
    echo "sudo apt update"
    echo "sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra"
    exit 1
fi

# 启动 OCR API
echo "启动 OCR API Server..."
echo "访问地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "按 Ctrl+C 停止服务"

# 使用虚拟环境中的Python运行
python ocr_api.py
