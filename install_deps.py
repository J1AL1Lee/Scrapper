#!/usr/bin/env python3
"""
安装项目依赖的脚本
"""

import subprocess
import sys
import os

def install_package(package_name, description=""):
    """安装Python包"""
    print(f"正在安装 {package_name}...")
    if description:
        print(f"  {description}")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✅ {package_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package_name} 安装失败: {e}")
        return False

def main():
    print("🚀 开始安装项目依赖...")
    print()
    
    # 基础依赖
    print("📦 安装基础依赖...")
    install_package("opencv-python-headless", "OpenCV图像处理库")
    install_package("pillow", "PIL图像处理库")
    install_package("numpy", "数值计算库")
    install_package("loguru", "日志库")
    install_package("playwright", "浏览器自动化库")
    install_package("asyncio", "异步编程库")
    print()
    
    # OCR引擎
    print("🔍 安装OCR引擎...")
    print("  注意：OCR引擎首次使用会下载中文模型，可能需要一些时间")
    print()
    
    # 尝试安装EasyOCR
    easyocr_success = install_package("easyocr", "EasyOCR文字识别库")
    
    # 尝试安装PaddleOCR
    paddleocr_success = install_package("paddlepaddle", "PaddlePaddle深度学习框架")
    if paddleocr_success:
        install_package("paddleocr", "PaddleOCR文字识别库")
    
    print()
    
    if easyocr_success or paddleocr_success:
        print("✅ OCR引擎安装完成！")
        if easyocr_success and paddleocr_success:
            print("   已安装EasyOCR和PaddleOCR，系统会自动选择最佳引擎")
        elif easyocr_success:
            print("   已安装EasyOCR")
        else:
            print("   已安装PaddleOCR")
    else:
        print("❌ 警告：没有安装任何OCR引擎，验证码识别功能将不可用")
    
    print()
    print("🎯 安装完成！现在可以运行项目了")
    print("   运行命令: python main.py")

if __name__ == "__main__":
    main()
