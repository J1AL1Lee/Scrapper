#!/usr/bin/env python3
"""
调试选择器脚本 - 帮助检查页面元素
"""
import asyncio
from playwright.async_api import async_playwright
from config import settings
from project_selectors import SELECTORS

async def debug_page():
    """调试页面元素"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=settings.user_agent,
            viewport={"width": settings.viewport[0], "height": settings.viewport[1]},
            locale=settings.locale,
            timezone_id=settings.timezone_id,
        )
        
        page = await context.new_page()
        
        print(f"正在访问: {settings.login_url}")
        await page.goto(settings.login_url, wait_until="networkidle")
        
        print("等待页面加载...")
        await asyncio.sleep(5)
        
        print("\n=== 页面信息 ===")
        print(f"页面标题: {await page.title()}")
        print(f"当前URL: {page.url}")
        
        print("\n=== 检查登录相关元素 ===")
        login_sel = SELECTORS["login"]
        
        for name, selector in login_sel.items():
            try:
                elements = await page.locator(selector).count()
                if elements > 0:
                    print(f"✓ {name}: {selector} (找到 {elements} 个)")
                    # 显示第一个元素的文本内容
                    first_element = page.locator(selector).first
                    try:
                        text = await first_element.inner_text()
                        if text.strip():
                            print(f"  文本内容: {text.strip()[:50]}...")
                    except:
                        pass
                else:
                    print(f"✗ {name}: {selector} (未找到)")
            except Exception as e:
                print(f"✗ {name}: {selector} (错误: {e})")
        
        print("\n=== 检查页面上的所有可能元素 ===")
        # 查找一些常见的元素
        common_selectors = [
            "input", "button", "img", "div", "span", "a",
            "[class*='user']", "[class*='login']", "[class*='captcha']",
            "[class*='submit']", "[class*='form']"
        ]
        
        for selector in common_selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    print(f"找到 {count} 个 {selector}")
                    # 显示前几个元素的class或id
                    for i in range(min(3, count)):
                        element = page.locator(selector).nth(i)
                        try:
                            class_attr = await element.get_attribute("class")
                            id_attr = await element.get_attribute("id")
                            if class_attr or id_attr:
                                print(f"  {i+1}: class='{class_attr}' id='{id_attr}'")
                        except:
                            pass
            except Exception as e:
                print(f"检查 {selector} 时出错: {e}")
        
        print("\n=== 调试完成 ===")
        print("请手动登录，然后按回车键继续...")
        input()
        
        print("登录后页面信息:")
        print(f"页面标题: {await page.title()}")
        print(f"当前URL: {page.url}")
        
        # 再次检查登录成功标记
        print("\n=== 登录后检查登录成功标记 ===")
        try:
            success_element = await page.wait_for_selector(login_sel["login_success_marker"], timeout=5000)
            if success_element:
                print(f"✓ 找到登录成功标记: {login_sel['login_success_marker']}")
                text = await success_element.inner_text()
                print(f"  内容: {text.strip()}")
            else:
                print("✗ 未找到登录成功标记")
        except Exception as e:
            print(f"✗ 等待登录成功标记超时: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
