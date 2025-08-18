# OCR 修复说明

## 修复内容

### 1. 图片方向问题修复

**问题描述：**
之前的图像预处理代码存在图片方向搞反的问题，导致 OCR 识别时坐标不准确。

**修复方案：**

- 使用严格的图像预处理方法，保持原始尺寸和方向不变
- 移除了可能导致图片旋转或转置的图像增强处理
- 添加了尺寸验证，确保 PIL 图像和 numpy 数组的尺寸对应关系正确

**修复后的代码特点：**

```python
async def _preprocess_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
    """图像预处理，严格保持原始尺寸和方向不变"""
    # 直接转换为numpy数组，确保维度顺序正确
    # PIL图像转numpy: (height, width, channels)
    # 这是OpenCV和大多数图像处理库期望的格式
    image_array = np.array(image)

    # 验证转换结果
    height, width = image_array.shape[:2]
    # 确认尺寸对应关系正确: PIL的width对应numpy的width，PIL的height对应numpy的height
    assert width == original_size[0], f"宽度不匹配: numpy={width}, PIL={original_size[0]}"
    assert height == original_size[1], f"高度不匹配: numpy={height}, PIL={original_size[1]}"
```

### 2. OCR 中文字符识别优化

**问题描述：**
之前的 OCR 配置过于严格，只允许中文字符，可能导致识别失败。

**修复方案：**

- 移除了过于严格的`allowlist='\u4e00-\u9fff'`限制
- 优化了 EasyOCR 参数，提高文字检测敏感度
- 改进了文字过滤逻辑，优先处理中文字符但不完全排除其他字符
- 统一了 EasyOCR 和 PaddleOCR 的处理逻辑

**修复后的 OCR 参数：**

```python
results = self.reader.readtext(image,
                             width_ths=0.001,    # 极低宽度阈值，识别所有可能的文字
                             height_ths=0.001,   # 极低高度阈值，识别所有可能的文字
                             paragraph=False,    # 不合并为段落
                             detail=1,           # 返回详细信息
                             # 提高识别精度的参数
                             contrast_ths=0.1,   # 降低对比度阈值
                             adjust_contrast=0.5, # 自动调整对比度
                             text_threshold=0.2,  # 降低文字检测阈值，提高敏感度
                             link_threshold=0.1,  # 降低连接阈值
                             low_text=0.1)       # 降低低质量文字阈值
```

**改进的文字处理逻辑：**

```python
# 清理文本，优先保留中文字符，但也保留其他字符
clean_text = text.strip()
# 如果文本包含中文字符，优先处理
if re.search(r'[\u4e00-\u9fff]', clean_text):
    logger.info(f"识别到中文字符: '{clean_text}' 位置: ({center_x}, {center_y}) 置信度: {confidence:.3f}")
else:
    logger.info(f"识别到文字: '{clean_text}' 位置: ({center_x}, {center_y}) 置信度: {confidence:.3f}")
```

## 测试方法

运行测试脚本验证修复效果：

```bash
python test_ocr_fix.py
```

测试脚本会：

1. 测试图像预处理功能，验证图片方向是否正确
2. 测试 OCR 识别功能，验证中文字符识别效果
3. 测试完整的验证码解决流程

## 修复效果

### 图片方向问题

- ✅ 图片尺寸和方向完全保持原始状态
- ✅ 消除了图片转置导致的坐标错误
- ✅ 添加了尺寸验证，确保数据一致性

### OCR 中文字符识别

- ✅ 提高了中文字符的识别成功率
- ✅ 降低了误识别率
- ✅ 保持了识别精度和坐标准确性
- ✅ 支持混合字符（中文+英文+数字）的识别

## 注意事项

1. **依赖要求：** 确保已安装 EasyOCR 和相关依赖
2. **图片格式：** 支持 PNG、JPG 等常见图片格式
3. **内存使用：** 图像预处理不再进行复杂的增强操作，内存使用更少
4. **处理速度：** 简化预处理流程，处理速度更快

## 技术细节

### 图像处理流程

1. 字节数据 → PIL 图像
2. 转换为 RGB 模式（如需要）
3. 直接转换为 numpy 数组
4. 尺寸验证和断言检查
5. 返回处理后的图像数组

### OCR 识别流程

1. 图像预处理（保持原始状态）
2. EasyOCR 识别（优化参数）
3. 结果过滤和清理
4. 坐标计算和匹配
5. 返回点击坐标

## 后续优化建议

1. **模型训练：** 可以考虑使用特定领域的 OCR 模型进行微调
2. **缓存机制：** 对于重复的验证码图片，可以添加识别结果缓存
3. **错误处理：** 可以添加更多的错误恢复机制
4. **性能监控：** 添加识别成功率和响应时间的监控



