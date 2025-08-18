#!/usr/bin/env python3
"""
调试工作台页面脚本 - 分析登录成功后的页面元素
"""
import asyncio
from playwright.async_api import async_playwright
from config import settings

async def debug_workbench():
    """调试工作台页面元素"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=settings.user_agent,
            viewport={"width": settings.viewport[0], "height": settings.viewport[1]},
            locale=settings.locale,
            timezone_id=settings.timezone_id,
        )
        
        page = await context.new_page()
        
        print("请手动登录，登录成功后脚本会自动分析工作台页面...")
        print("登录URL:", settings.login_url)
        
        await page.goto(settings.login_url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        # 等待用户手动登录
        print("\n请在浏览器中完成登录...")
        print("登录成功后按回车键继续...")
        input()
        
        print("\n=== 登录后页面分析 ===")
        print(f"页面标题: {await page.title()}")
        print(f"当前URL: {page.url}")
        
        # 等待页面稳定
        await asyncio.sleep(3)
        
        print("\n=== 查找可能的登录成功标记 ===")
        
        # 尝试多种可能的选择器
        possible_selectors = [
            # 用户信息相关
            ".user-info", ".user-menu", ".user-profile", ".user-avatar",
            ".avatar", ".profile", ".user-name", ".user-account",
            
            # 导航菜单相关
            ".nav-menu", ".sidebar", ".menu", ".navigation",
            ".header", ".top-bar", ".toolbar",
            
            # 工作台特有元素
            ".workbench", ".dashboard", ".main-content", ".content-area",
            ".welcome", ".greeting", ".user-greeting",
            
            # 通用元素
            "[class*='user']", "[class*='profile']", "[class*='avatar']",
            "[class*='menu']", "[class*='nav']", "[class*='header']",
            
            # 按钮和链接
            "button", "a", ".btn", ".link",
            
            # 文本内容
            "span", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6"
        ]
        
        found_elements = []
        
        for selector in possible_selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    print(f"\n找到 {count} 个 {selector}")
                    
                    # 分析前几个元素
                    for i in range(min(3, count)):
                        element = page.locator(selector).nth(i)
                        try:
                            # 获取元素属性
                            class_attr = await element.get_attribute("class")
                            id_attr = await element.get_attribute("id")
                            text_content = await element.inner_text()
                            
                            # 检查是否包含用户相关信息
                            is_user_related = any(keyword in (class_attr or "").lower() for keyword in 
                                                ['user', 'profile', 'avatar', 'name', 'account', 'login', 'logout'])
                            
                            if is_user_related or (text_content and len(text_content.strip()) < 50):
                                print(f"  {i+1}: class='{class_attr}' id='{id_attr}'")
                                if text_content.strip():
                                    print(f"    文本: {text_content.strip()}")
                                
                                # 检查是否可见
                                is_visible = await element.is_visible()
                                print(f"    可见: {is_visible}")
                                
                                if is_user_related:
                                    found_elements.append({
                                        'selector': selector,
                                        'index': i,
                                        'class': class_attr,
                                        'id': id_attr,
                                        'text': text_content.strip(),
                                        'visible': is_visible
                                    })
                                    
                        except Exception as e:
                            print(f"    分析元素 {i+1} 时出错: {e}")
                            
            except Exception as e:
                print(f"检查 {selector} 时出错: {e}")
        
        print(f"\n=== 找到 {len(found_elements)} 个可能的用户相关元素 ===")
        for i, elem in enumerate(found_elements):
            print(f"{i+1}. {elem['selector']} (第{elem['index']+1}个)")
            print(f"   class: {elem['class']}")
            print(f"   id: {elem['id']}")
            print(f"   文本: {elem['text']}")
            print(f"   可见: {elem['visible']}")
            print()
        
        # 尝试保存会话状态
        print("=== 尝试保存会话状态 ===")
        try:
            await context.storage_state(path="test_storage.json")
            print("✓ 会话状态保存成功: test_storage.json")
        except Exception as e:
            print(f"✗ 会话状态保存失败: {e}")
        
        print("\n=== 调试完成 ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_workbench())
