# DDDOCR 验证码识别器使用说明

## 概述

本项目已升级为使用 **ddddocr** 进行验证码识别，这是一个高效的本地 OCR 识别库，特别适合中文验证码识别。

## 主要特性

- 🚀 **高效识别**: 使用 ddddocr 进行快速准确的汉字识别
- 🎯 **智能定位**: 自动检测验证码中的文字区域
- 🔄 **多角度识别**: 支持旋转图像以提高识别率
- 📍 **精确点击**: 根据识别结果生成准确的点击坐标
- 🖼️ **调试支持**: 生成带标注的结果图片用于调试

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包括：

- `ddddocr>=1.4.11` - 核心 OCR 识别库
- `opencv-python>=4.8.0` - 图像处理
- `Pillow>=10.0.0` - 图像操作
- `numpy>=1.24.0` - 数值计算

## 使用方法

### 1. 基本使用

```python
from captcha.ddddocr_solver import DdddOcrClickCaptchaSolver

# 初始化识别器
solver = DdddOcrClickCaptchaSolver()

# 识别验证码
result = await solver.solve_captcha(image_bytes, instruction)
```

### 2. 命令行使用

```bash
# 使用ddddocr识别器（默认）
python main.py

# 明确指定使用ddddocr
python main.py --use-solver ocr

# 若快在线服务（如果配置了）
python main.py --use-solver ruokuai
```

### 3. 验证码指令格式

支持多种指令格式：

- `请依次点击【加,书,话】`
- `点击加、书、话`
- `按顺序点击加书话`
- `找出加书话`

## 识别流程

1. **图像预处理**: 转换为灰度图，二值化，去噪
2. **目标检测**: 使用 ddddocr 检测可能的文字区域
3. **OCR 识别**: 对每个区域进行汉字识别
4. **指令解析**: 解析验证码指令，提取目标汉字
5. **坐标匹配**: 根据识别结果匹配目标汉字位置
6. **结果输出**: 生成点击坐标和调试图片

## 输出结果

识别成功时返回：

```python
{
    "success": True,
    "click_points": [
        {
            "x": 100,
            "y": 150,
            "char": "加",
            "confidence": 0.95
        },
        {
            "x": 200,
            "y": 150,
            "char": "书",
            "confidence": 0.92
        }
    ],
    "debug_image": "result.png"
}
```

## 调试功能

- 自动生成 `result.png` 调试图片
- 红框标注检测到的文字区域
- 绿色文字显示识别结果
- 蓝色圆圈标记点击位置

## 测试

运行测试脚本验证识别器：

```bash
python test_ddddocr.py
```

确保 `image.png` 文件存在（验证码图片）。

## 性能优化

- 使用第二套 OCR 模型提高识别率
- 支持多角度识别（-15° 到 +15°）
- 智能图像预处理
- 缓存机制减少重复计算

## 故障排除

### 常见问题

1. **ddddocr 初始化失败**

   - 检查是否安装了 ddddocr: `pip install ddddocr`
   - 确保网络连接正常（首次使用需要下载模型）

2. **识别准确率低**

   - 检查图像质量
   - 尝试调整图像预处理参数
   - 确保验证码图片清晰

3. **点击坐标错误**
   - 检查调试图片中的标注
   - 验证验证码图片边界框获取是否正确

### 日志输出

程序会输出详细的识别过程日志，包括：

- 检测到的区域数量
- 每个区域的识别结果
- 点击坐标计算过程
- 错误信息和异常堆栈

## 升级说明

从旧版 OCR 升级到 ddddocr：

1. 删除了所有旧的 OCR 相关代码
2. 替换为新的 ddddocr 识别器
3. 保持了原有的 API 接口
4. 增强了识别准确率和性能

## 技术细节

- **目标检测**: 使用 ddddocr 的 detection 功能
- **文字识别**: 使用 ddddocr 的 classification 功能
- **图像处理**: OpenCV + PIL 组合处理
- **坐标系统**: 相对坐标转换为绝对坐标
- **异步支持**: 全异步操作，提高并发性能


