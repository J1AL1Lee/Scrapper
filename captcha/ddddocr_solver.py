import ddddocr
import cv2
import numpy as np
from PIL import Image
import math
import io
import asyncio
from loguru import logger
from typing import List, Tuple, Dict, Optional

class DdddOcrClickCaptchaSolver:
    """使用ddddocr的点击验证码识别器"""
    
    def __init__(self):
        try:
            # 初始化目标检测和OCR识别（使用第二套模型提高识别率）
            self.det = ddddocr.DdddOcr(det=True)
            self.ocr = ddddocr.DdddOcr(beta=True)  # 使用第二套OCR模型
            logger.info("ddddocr验证码识别器初始化成功")
        except Exception as e:
            logger.error(f"ddddocr初始化失败: {e}")
            raise
    
    def preprocess_roi(self, roi):
        """预处理ROI图像，提高识别率"""
        # 转换为灰度图
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi
        
        # 二值化处理
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 去噪
        denoised = cv2.medianBlur(binary, 3)
        
        return denoised
    
    def rotate_image(self, image, angle):
        """旋转图像"""
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # 计算旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 执行旋转
        rotated = cv2.warpAffine(image, rotation_matrix, (width, height), 
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
        return rotated
    
    def try_multiple_angles(self, roi_bytes, angles=[-15, -10, -5, 0, 5, 10, 15]):
        """尝试多个角度进行OCR识别"""
        best_result = ""
        best_confidence = 0
        
        # 首先尝试原始角度
        try:
            result = self.ocr.classification(roi_bytes)
            if result and len(result.strip()) > 0:
                return result, 1.0
        except:
            pass
        
        # 尝试不同角度
        for angle in angles:
            try:
                # 将字节转换为PIL图像进行旋转
                pil_img = Image.open(io.BytesIO(roi_bytes))
                rotated_pil = pil_img.rotate(angle, expand=True, fillcolor=255)
                
                # 转换回字节
                rotated_bytes = io.BytesIO()
                rotated_pil.save(rotated_bytes, format='PNG')
                rotated_bytes = rotated_bytes.getvalue()
                
                # OCR识别
                result = self.ocr.classification(rotated_bytes)
                if result and len(result.strip()) > 0:
                    return result, 0.8  # 旋转后的结果置信度稍低
                    
            except Exception as e:
                continue
        
        return "", 0.0
    
    def _parse_instruction(self, instruction: str) -> List[str]:
        """解析验证码指令，提取需要点击的汉字"""
        if not instruction:
            return []
        
        # 常见的指令格式
        instruction_patterns = [
            "请依次点击", "请点击", "点击", "选择", "找出"
        ]
        
        # 提取汉字
        target_chars = []
        for pattern in instruction_patterns:
            if pattern in instruction:
                # 提取指令后面的汉字
                start_idx = instruction.find(pattern) + len(pattern)
                remaining = instruction[start_idx:].strip()
                
                # 提取汉字（中文字符）
                for char in remaining:
                    if '\u4e00' <= char <= '\u9fff':  # 汉字Unicode范围
                        target_chars.append(char)
                
                if target_chars:
                    break
        
        # 如果没有找到模式，尝试直接提取所有汉字
        if not target_chars:
            for char in instruction:
                if '\u4e00' <= char <= '\u9fff':
                    target_chars.append(char)
        
        logger.info(f"解析指令 '{instruction}' 得到目标汉字: {target_chars}")
        return target_chars
    
    async def solve_captcha(self, image_bytes: bytes, instruction: str = "") -> Dict:
        """识别点击验证码中的汉字位置"""
        try:
            # 解析指令，提取需要点击的汉字
            target_chars = self._parse_instruction(instruction)
            if not target_chars:
                return {"success": False, "error": "无法解析验证码指令"}
            
            logger.info(f"需要点击的汉字: {target_chars}")
            
            # 目标检测，获取可能的文字区域
            bboxes = self.det.detection(image_bytes)
            logger.info(f"检测到的区域数量: {len(bboxes)}")
            
            if not bboxes:
                return {"success": False, "error": "未检测到任何文字区域"}
            
            # 将字节转换为OpenCV图像
            nparr = np.frombuffer(image_bytes, np.uint8)
            im = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 对每个检测到的区域进行OCR识别
            char_regions = []
            for i, bbox in enumerate(bboxes):
                x1, y1, x2, y2 = bbox
                
                # 提取该区域的图像进行OCR识别
                roi = im[y1:y2, x1:x2]
                
                # 将ROI转换为字节格式进行OCR识别
                _, roi_encoded = cv2.imencode('.png', roi)
                roi_bytes = roi_encoded.tobytes()
                
                try:
                    # 尝试多角度识别
                    text, confidence = self.try_multiple_angles(roi_bytes)
                    
                    if text and confidence > 0:
                        logger.info(f"区域 {i+1}: 识别结果 = '{text}' (置信度: {confidence:.2f})")
                        
                        char_regions.append({
                            'text': text,
                            'bbox': bbox,
                            'center_x': (x1 + x2) // 2,
                            'center_y': (y1 + y2) // 2,
                            'confidence': confidence
                        })
                    else:
                        logger.warning(f"区域 {i+1}: 识别失败 - 未识别到有效文字")
                        
                except Exception as e:
                    logger.error(f"区域 {i+1}: OCR识别异常 - {e}")
                    continue
            
            # 根据指令顺序查找汉字并生成点击坐标
            click_points = []
            used_regions = set()
            
            for target_char in target_chars:
                best_match = None
                best_confidence = 0
                
                for region in char_regions:
                    # 将bbox转换为元组以便在集合中使用
                    bbox_tuple = tuple(region['bbox'])
                    if region['text'] == target_char and bbox_tuple not in used_regions:
                        if region['confidence'] > best_confidence:
                            best_match = region
                            best_confidence = region['confidence']
                
                if best_match:
                    click_points.append({
                        'x': best_match['center_x'],
                        'y': best_match['center_y'],
                        'char': target_char,
                        'confidence': best_match['confidence']
                    })
                    used_regions.add(tuple(best_match['bbox']))
                    logger.info(f"找到汉字 '{target_char}' 的点击位置: ({best_match['center_x']}, {best_match['center_y']})")
                else:
                    logger.warning(f"未找到汉字 '{target_char}' 的匹配区域")
            
            # 生成结果图像用于调试
            result_im = im.copy()
            for i, bbox in enumerate(bboxes):
                x1, y1, x2, y2 = bbox
                # 在图像上绘制红框
                result_im = cv2.rectangle(result_im, (x1, y1), (x2, y2), color=(0, 0, 255), thickness=2)
                
                # 查找对应的识别结果
                for region in char_regions:
                    if tuple(region['bbox']) == tuple(bbox):
                        # 在图像上显示识别结果（绿色）
                        cv2.putText(result_im, region['text'], (x1, y1-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        break
            
            # 标记点击点（蓝色圆圈）
            for point in click_points:
                cv2.circle(result_im, (point['x'], point['y']), 5, (255, 0, 0), -1)
                cv2.putText(result_im, f"点击", (point['x']+10, point['y']-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # 保存结果图像
            cv2.imwrite("result.png", result_im)
            logger.info("处理完成，结果已保存到 result.png")
            
            if click_points:
                # 检查是否找到了所有目标汉字
                found_chars = [point['char'] for point in click_points]
                missing_chars = [char for char in target_chars if char not in found_chars]
                
                if missing_chars:
                    logger.warning(f"只找到部分汉字: {found_chars}, 缺少: {missing_chars}")
                    return {
                        "success": False, 
                        "error": f"只找到部分汉字: {found_chars}, 缺少: {missing_chars}",
                        "partial_success": True,
                        "found_chars": found_chars,
                        "missing_chars": missing_chars,
                        "click_points": click_points,
                        "debug_image": "result.png"
                    }
                else:
                    logger.info(f"成功识别所有目标汉字: {found_chars}")
                    return {
                        "success": True,
                        "click_points": click_points,
                        "debug_image": "result.png"
                    }
            else:
                return {"success": False, "error": "未找到任何匹配的点击点"}
                
        except Exception as e:
            logger.error(f"验证码识别过程中发生异常: {e}")
            return {"success": False, "error": f"识别异常: {str(e)}"}
    
    def get_click_coordinates(self, click_points: List[Dict]) -> List[Tuple[int, int]]:
        """获取点击坐标列表"""
        return [(point['x'], point['y']) for point in click_points]
