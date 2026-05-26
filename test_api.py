#!/usr/bin/env python3
"""
OCR API 测试脚本
"""

import requests
import json
import os
from PIL import Image, ImageDraw, ImageFont

def create_test_image():
    """创建一个测试图片"""
    # 创建一个白色背景的图片
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # 尝试使用默认字体，如果没有则使用内置字体
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
    
    # 绘制文字
    text = "Hello OCR!\n这是一个测试图片\n识别文字内容"
    draw.text((10, 10), text, fill='black', font=font)
    
    return img

def test_ocr_api():
    """测试OCR API"""
    base_url = "http://localhost:8000"
    
    print("🧪 开始测试 OCR API...")
    
    # 1. 测试健康检查
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ 健康检查: {health_data['status']}")
            if not health_data['tesseract_available']:
                print("⚠️  Tesseract 未安装，请先安装: sudo apt install tesseract-ocr tesseract-ocr-chi-sim")
                return False
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 OCR API，请确保服务已启动")
        print("启动命令: cd ~/.openclaw/workspace && ./start_ocr_api.sh")
        return False
    
    # 2. 创建测试图片
    print("📝 创建测试图片...")
    test_img = create_test_image()
    img_path = "test_image.png"
    test_img.save(img_path)
    
    # 3. 测试单图片OCR
    print("🔍 测试单图片OCR...")
    try:
        with open(img_path, 'rb') as f:
            files = {'file': f}
            data = {
                'language': 'chi_sim+eng',
                'detailed': 'true'
            }
            
            response = requests.post(f"{base_url}/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ OCR识别成功")
                print(f"📊 识别文字: {result['text']}")
                print(f"📝 单词数量: {result['word_count']}")
                print(f"⏱️  处理时间: {result['processing_time']}秒")
                print(f"🎯 平均置信度: {result['average_confidence']}%")
                
                if 'detailed_data' in result:
                    print(f"📦 检测到 {result['detailed_data']['boxes']} 个文本框")
            else:
                print(f"❌ OCR识别失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False
    
    # 4. 清理测试文件
    if os.path.exists(img_path):
        os.remove(img_path)
    
    print("🎉 所有测试通过！")
    return True

if __name__ == "__main__":
    test_ocr_api()