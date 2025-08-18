#!/usr/bin/env python3
"""
测试ddddocr验证码识别器的错误处理和刷新功能
"""

import asyncio
import os
from loguru import logger
from captcha.ddddocr_solver import DdddOcrClickCaptchaSolver

async def test_error_handling():
    """测试错误处理逻辑"""
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
        
        # 测试1: 完全匹配的情况
        logger.info("\n=== 测试1: 完全匹配的情况 ===")
        test_instruction = "请依次点击【圈,谁,船】"  # 使用图片中实际存在的汉字
        
        result = await solver.solve_captcha(image_bytes, test_instruction)
        
        if result.get("success"):
            logger.info("✅ 完全匹配测试成功!")
            click_points = result.get("click_points", [])
            logger.info(f"识别到 {len(click_points)} 个点击点:")
            
            for i, point in enumerate(click_points):
                logger.info(f"  点 {i+1}: 汉字 '{point['char']}' 位置 ({point['x']}, {point['y']}) 置信度 {point['confidence']:.2f}")
        else:
            logger.error(f"❌ 完全匹配测试失败: {result.get('error', '未知错误')}")
        
        # 测试2: 部分匹配的情况
        logger.info("\n=== 测试2: 部分匹配的情况 ===")
        test_instruction = "请依次点击【圈,谁,加】"  # 部分汉字存在，部分不存在
        
        result = await solver.solve_captcha(image_bytes, test_instruction)
        
        if result.get("partial_success"):
            logger.info("✅ 部分匹配测试成功!")
            found_chars = result.get("found_chars", [])
            missing_chars = result.get("missing_chars", [])
            click_points = result.get("click_points", [])
            
            logger.info(f"找到的汉字: {found_chars}")
            logger.info(f"缺少的汉字: {missing_chars}")
            logger.info(f"点击点数量: {len(click_points)}")
            
            for i, point in enumerate(click_points):
                logger.info(f"  点 {i+1}: 汉字 '{point['char']}' 位置 ({point['x']}, {point['y']}) 置信度 {point['confidence']:.2f}")
        else:
            logger.error(f"❌ 部分匹配测试失败: {result.get('error', '未知错误')}")
        
        # 测试3: 完全不匹配的情况
        logger.info("\n=== 测试3: 完全不匹配的情况 ===")
        test_instruction = "请依次点击【加,书,话】"  # 所有汉字都不存在
        
        result = await solver.solve_captcha(image_bytes, test_instruction)
        
        if not result.get("success") and not result.get("partial_success"):
            logger.info("✅ 完全不匹配测试成功!")
            logger.info(f"错误信息: {result.get('error', '未知错误')}")
        else:
            logger.error(f"❌ 完全不匹配测试失败: 意外成功")
        
        # 测试4: 指令解析功能
        logger.info("\n=== 测试4: 指令解析功能 ===")
        test_instructions = [
            "请依次点击【加,书,话】",
            "点击加、书、话",
            "按顺序点击加书话",
            "找出加书话",
            "请点击加书话",
            "选择加书话"
        ]
        
        for instruction in test_instructions:
            target_chars = solver._parse_instruction(instruction)
            logger.info(f"指令: '{instruction}' -> 解析结果: {target_chars}")
        
        logger.info("\n🎉 所有测试完成!")
        
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_error_handling())

