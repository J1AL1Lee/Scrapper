#!/usr/bin/env python3
"""
测试ddddocr验证码识别器
"""

import asyncio
import os
from loguru import logger
from captcha.ddddocr_solver import DdddOcrClickCaptchaSolver

async def test_ddddocr_solver():
    """测试ddddocr验证码识别器"""
    try:
        # 初始化识别器
        logger.info("初始化ddddocr验证码识别器...")
        solver = DdddOcrClickCaptchaSolver()
        logger.info("✅ ddddocr验证码识别器初始化成功")
        
        # 检查是否有测试图片
        test_image_path = "image.png"
        if not os.path.exists(test_image_path):
            logger.error(f"测试图片 {test_image_path} 不存在")
            logger.info("请将验证码图片保存为 image.png 进行测试")
            return
        
        # 读取测试图片
        logger.info(f"读取测试图片: {test_image_path}")
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
        
        # 测试指令解析
        test_instructions = [
            "请依次点击【加,书,话】",
            "点击加、书、话",
            "按顺序点击加书话",
            "找出加书话"
        ]
        
        for instruction in test_instructions:
            logger.info(f"\n测试指令: {instruction}")
            target_chars = solver._parse_instruction(instruction)
            logger.info(f"解析结果: {target_chars}")
        
        # 测试验证码识别
        logger.info("\n开始验证码识别测试...")
        test_instruction = "请依次点击【加,书,话】"
        
        result = await solver.solve_captcha(image_bytes, test_instruction)
        
        if result.get("success"):
            logger.info("✅ 验证码识别成功!")
            click_points = result.get("click_points", [])
            logger.info(f"识别到 {len(click_points)} 个点击点:")
            
            for i, point in enumerate(click_points):
                logger.info(f"  点 {i+1}: 汉字 '{point['char']}' 位置 ({point['x']}, {point['y']}) 置信度 {point['confidence']:.2f}")
            
            if result.get("debug_image"):
                logger.info(f"调试图片已保存为: {result['debug_image']}")
        else:
            logger.error(f"❌ 验证码识别失败: {result.get('error', '未知错误')}")
        
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ddddocr_solver())


