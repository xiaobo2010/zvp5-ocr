#!/usr/bin/env python3
"""
OCR API Server using pytesseract + FastAPI
支持图片文件上传，返回JSON格式OCR结果
"""

import os
import io
import time
import signal
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OCR API Server",
    description="基于 pytesseract 的图片文字识别 API",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OCR 配置
class OCRConfig:
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.timeout = 30  # 30秒超时
        
    def is_supported_format(self, filename: str) -> bool:
        """检查文件格式是否支持"""
        return any(filename.lower().endswith(ext) for ext in self.supported_formats)

# OCR处理器
class OCRProcessor:
    def __init__(self):
        self.config = OCRConfig()
        
    def _ocr_with_timeout(self, image: Image.Image, lang: str, timeout: int):
        """带超时控制的OCR处理，防止大图卡死worker"""
        result_holder: Dict[str, Any] = {"result": None, "error": None}

        def _worker():
            try:
                text = pytesseract.image_to_string(image, lang=lang)
                data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
                result_holder["result"] = (text, data)
            except Exception as ex:
                result_holder["error"] = ex

        # 在子进程中执行OCR，利用SIGALRM实现超时
        import threading
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # 超时，线程仍在运行（但因daemon=True不会阻止进程退出）
            return None, TimeoutError(f"OCR处理超时（>{timeout}秒），图片可能过大或过于复杂")

        if result_holder["error"] is not None:
            return None, result_holder["error"]

        return result_holder["result"], None

    def extract_text(self, image: Image.Image, lang: str = 'chi_sim+eng') -> Dict[str, Any]:
        """从图片中提取文字"""
        try:
            start_time = time.time()

            # 带超时的OCR处理
            ocr_result, error = self._ocr_with_timeout(image, lang, self.config.timeout)
            if error is not None:
                raise error

            text, data = ocr_result

            # 统计信息
            processing_time = time.time() - start_time
            word_count = len(text.split())

            # 安全转换置信度值，防止非数字值导致崩溃
            confidence_scores = []
            for conf in data['conf']:
                try:
                    val = int(conf)
                    if val > 0:
                        confidence_scores.append(val)
                except (ValueError, TypeError):
                    continue
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

            return {
                "success": True,
                "text": text.strip(),
                "word_count": word_count,
                "processing_time": round(processing_time, 2),
                "average_confidence": round(avg_confidence, 2),
                "detailed_data": {
                    "boxes": len(data['text']),
                    "words_with_confidence": [
                        {
                            "text": data['text'][i],
                            "confidence": confidence_scores[j] if j < len(confidence_scores) else 0,
                            "bbox": {
                                "x": data['left'][i],
                                "y": data['top'][i],
                                "width": data['width'][i],
                                "height": data['height'][i]
                            }
                        }
                        for j, i in enumerate(
                            idx for idx in range(len(data['text']))
                            if _safe_int(data['conf'][idx], 0) > 0
                        )
                    ]
                }
            }

        except TimeoutError as e:
            logger.error(f"OCR处理超时: {str(e)}")
            return {
                "success": False,
                "error": "TIMEOUT",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"OCR处理失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "OCR处理过程中发生错误"
            }

def _safe_int(value, default=0) -> int:
    """安全地将值转换为int，失败时返回默认值"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# 全局OCR处理器
ocr_processor = OCRProcessor()

@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "OCR API Server 运行中",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 测试tesseract是否可用
        test_text = pytesseract.get_languages(config='')
        return {
            "status": "healthy",
            "tesseract_available": True,
            "available_languages": test_text.split(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "tesseract_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/upload")
async def upload_and_ocr(
    file: UploadFile = File(...),
    language: str = "chi_sim+eng",
    detailed: bool = False
) -> JSONResponse:
    """
    上传图片文件进行OCR识别
    
    Args:
        file: 图片文件
        language: OCR语言 (默认: chi_sim+eng)
        detailed: 是否返回详细数据 (默认: False)
    
    Returns:
        JSONResponse: OCR识别结果
    """
    # 验证文件格式
    if not ocr_processor.config.is_supported_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(ocr_processor.config.supported_formats)}"
        )
    
    # 验证文件大小
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # 重置文件指针
    
    if file_size > ocr_processor.config.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大。最大支持: {ocr_processor.config.max_file_size / 1024 / 1024}MB"
        )
    
    try:
        # 读取图片
        image = Image.open(io.BytesIO(contents))
        
        # 转换为兼容模式
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # OCR处理
        result = ocr_processor.extract_text(image, language)
        
        # 根据参数调整返回格式
        if not detailed:
            result.pop('detailed_data', None)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"处理上传文件失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理文件时发生错误: {str(e)}"
        )

@app.post("/batch-upload")
async def batch_upload_and_ocr(
    files: list[UploadFile] = File(...),
    language: str = "chi_sim+eng"
) -> JSONResponse:
    """
    批量上传图片文件进行OCR识别
    
    Args:
        files: 图片文件列表
        language: OCR语言
    
    Returns:
        JSONResponse: 批量OCR识别结果
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="批量上传最多支持10个文件"
        )
    
    results = []
    
    for file in files:
        try:
            # 验证文件格式
            if not ocr_processor.config.is_supported_format(file.filename):
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "不支持的文件格式"
                })
                continue
            
            # 验证文件大小
            contents = await file.read()
            if len(contents) > ocr_processor.config.max_file_size:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"文件过大，最大支持{ocr_processor.config.max_file_size / 1024 / 1024:.0f}MB"
                })
                continue

            # 读取图片
            image = Image.open(io.BytesIO(contents))

            # 转换为兼容模式
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')

            # OCR处理
            result = ocr_processor.extract_text(image, language)
            result["filename"] = file.filename
            results.append(result)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return JSONResponse(content={"results": results})

if __name__ == "__main__":
    import uvicorn
    
    print("启动 OCR API Server...")
    print("访问地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    
    uvicorn.run(
        "ocr_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )