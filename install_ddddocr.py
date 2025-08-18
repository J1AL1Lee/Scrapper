#!/usr/bin/env python3
"""
安装ddddocr和相关依赖的脚本
"""

import subprocess
import sys
import os

def run_command(command, description):
    """运行命令并显示进度"""
    print(f"正在{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description}成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        return False
    print(f"✅ Python版本: {sys.version}")
    return True

def install_dependencies():
    """安装依赖"""
    dependencies = [
        ("pip install --upgrade pip", "升级pip"),
        ("pip install ddddocr>=1.4.11", "安装ddddocr"),
        ("pip install opencv-python>=4.8.0", "安装OpenCV"),
        ("pip install Pillow>=10.0.0", "安装Pillow"),
        ("pip install numpy>=1.24.0", "安装NumPy"),
        ("pip install loguru>=0.7.0", "安装Loguru"),
        ("pip install playwright>=1.40.0", "安装Playwright"),
        ("pip install pydantic>=2.0.0", "安装Pydantic")
    ]
    
    success_count = 0
    for command, description in dependencies:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"⚠️  {description}失败，但继续安装其他依赖...")
    
    return success_count, len(dependencies)

def install_playwright_browsers():
    """安装Playwright浏览器"""
    print("正在安装Playwright浏览器...")
    try:
        result = subprocess.run("playwright install chromium", shell=True, check=True, capture_output=True, text=True)
        print("✅ Playwright浏览器安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Playwright浏览器安装失败: {e}")
        return False

def test_ddddocr():
    """测试ddddocr是否正常工作"""
    print("正在测试ddddocr...")
    try:
        import ddddocr
        det = ddddocr.DdddOcr(det=True)
        ocr = ddddocr.DdddOcr(beta=True)
        print("✅ ddddocr测试成功")
        return True
    except Exception as e:
        print(f"❌ ddddocr测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 DDDOCR验证码识别器安装脚本")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return
    
    # 安装依赖
    print("\n📦 安装依赖包...")
    success_count, total_count = install_dependencies()
    
    if success_count < total_count * 0.8:  # 如果成功率低于80%
        print(f"\n⚠️  部分依赖安装失败 ({success_count}/{total_count})")
        print("建议检查网络连接或使用国内镜像源")
        print("可以使用以下命令使用国内镜像源:")
        print("pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ ddddocr")
    
    # 安装Playwright浏览器
    print("\n🌐 安装Playwright浏览器...")
    install_playwright_browsers()
    
    # 测试ddddocr
    print("\n🧪 测试ddddocr...")
    if test_ddddocr():
        print("\n🎉 安装完成！")
        print("\n使用方法:")
        print("1. 运行测试: python test_ddddocr.py")
        print("2. 运行主程序: python main.py")
        print("3. 查看说明: cat DDDOCR_README.md")
    else:
        print("\n❌ 安装可能存在问题，请检查错误信息")
        print("常见解决方案:")
        print("1. 使用国内镜像源: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ ddddocr")
        print("2. 升级pip: python -m pip install --upgrade pip")
        print("3. 检查网络连接")

if __name__ == "__main__":
    main()


