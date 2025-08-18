#!/usr/bin/env python3
"""
探索工作台页面结构，找到正确的课程页面
"""
import asyncio
from playwright.async_api import async_playwright
from config import settings

async def explore_workbench():
    """探索工作台页面结构"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        
        # 使用已保存的会话状态
        context = await browser.new_context(
            storage_state="test_login_success.json",
            user_agent=settings.user_agent,
            viewport={"width": settings.viewport[0], "height": settings.viewport[1]},
            locale=settings.locale,
            timezone_id=settings.timezone_id,
        )
        
        page = await context.new_page()
        
        print("=== 探索工作台页面结构 ===")
        
        # 访问工作台页面
        workbench_url = "https://saas.psyyun.com/#/wel/index"
        print(f"访问工作台: {workbench_url}")
        
        await page.goto(workbench_url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        print(f"当前页面: {page.url}")
        print(f"页面标题: {await page.title()}")
        
        print("\n=== 查找导航菜单 ===")
        
        # 查找可能的导航元素
        nav_selectors = [
            "nav", ".nav", ".navigation", ".menu", ".sidebar",
            "[class*='nav']", "[class*='menu']", "[class*='sidebar']",
            "ul", "ol", ".el-menu", ".ant-menu"
        ]
        
        for selector in nav_selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    print(f"\n找到 {count} 个 {selector}")
                    
                    # 分析前几个元素
                    for i in range(min(5, count)):
                        try:
                            element = page.locator(selector).nth(i)
                            class_attr = await element.get_attribute("class")
                            text_content = await element.inner_text()
                            
                            if text_content.strip():
                                print(f"  {i+1}: class='{class_attr}'")
                                print(f"     文本: {text_content.strip()[:100]}...")
                                
                                # 查找链接
                                links = element.locator("a")
                                link_count = await links.count()
                                if link_count > 0:
                                    print(f"     包含 {link_count} 个链接")
                                    for j in range(min(3, link_count)):
                                        try:
                                            link = links.nth(j)
                                            href = await link.get_attribute("href")
                                            link_text = await link.inner_text()
                                            if href and link_text.strip():
                                                print(f"       - {link_text.strip()}: {href}")
                                        except Exception:
                                            pass
                                            
                        except Exception as e:
                            print(f"    分析元素 {i+1} 时出错: {e}")
                            
            except Exception as e:
                print(f"检查 {selector} 时出错: {e}")
        
        print("\n=== 查找所有链接 ===")
        
        # 查找页面上的所有链接
        try:
            all_links = page.locator("a")
            link_count = await all_links.count()
            print(f"找到 {link_count} 个链接")
            
            # 分析前20个链接
            for i in range(min(20, link_count)):
                try:
                    link = all_links.nth(i)
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    
                    if href and text.strip():
                        # 检查是否包含课程相关关键词
                        course_keywords = ['课程', 'course', '学习', 'study', '培训', 'training']
                        is_course_related = any(keyword in text.lower() or keyword in href.lower() for keyword in course_keywords)
                        
                        if is_course_related:
                            print(f"  🎯 课程相关: {text.strip()} -> {href}")
                        else:
                            print(f"  {i+1}: {text.strip()} -> {href}")
                            
                except Exception as e:
                    print(f"  分析链接 {i+1} 时出错: {e}")
                    
        except Exception as e:
            print(f"查找链接时出错: {e}")
        
        print("\n=== 查找按钮 ===")
        
        # 查找按钮
        try:
            buttons = page.locator("button")
            button_count = await buttons.count()
            print(f"找到 {button_count} 个按钮")
            
            for i in range(min(10, button_count)):
                try:
                    button = buttons.nth(i)
                    text = await button.inner_text()
                    class_attr = await button.get_attribute("class")
                    
                    if text.strip():
                        print(f"  {i+1}: {text.strip()} (class='{class_attr}')")
                        
                except Exception as e:
                    print(f"  分析按钮 {i+1} 时出错: {e}")
                    
        except Exception as e:
            print(f"查找按钮时出错: {e}")
        
        print("\n=== 探索完成 ===")
        print("请手动点击页面上的导航菜单，找到课程相关页面")
        print("然后告诉我正确的课程页面URL")
        
        # 保持浏览器打开，让用户手动探索
        print("\n按回车键关闭浏览器...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_workbench())
