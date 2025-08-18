#!/usr/bin/env python3
"""
简单的页面探索脚本
"""
import asyncio
from playwright.async_api import async_playwright
from config import settings

async def simple_explore():
    """简单的页面探索"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        
        # 创建新的上下文
        context = await browser.new_context(
            user_agent=settings.user_agent,
            viewport={"width": settings.viewport[0], "height": settings.viewport[1]},
            locale=settings.locale,
            timezone_id=settings.timezone_id,
        )
        
        page = await context.new_page()
        
        print("=== 简单页面探索 ===")
        print("1. 脚本会打开浏览器")
        print("2. 请手动完成登录")
        print("3. 登录成功后，在工作台页面找到课程相关菜单")
        print("4. 点击进入课程页面，记录URL")
        print("5. 按回车键继续...")
        
        # 访问登录页面
        await page.goto(settings.login_url, wait_until="networkidle")
        
        print("\n请在浏览器中完成登录...")
        input("登录成功后按回车键继续...")
        
        # 检查当前页面
        current_url = page.url
        current_title = await page.title()
        print(f"\n当前页面:")
        print(f"  URL: {current_url}")
        print(f"  标题: {current_title}")
        
        if "/wel/index" in current_url or "工作台" in current_title:
            print("✅ 已成功进入工作台页面")
            
            # 保存会话状态
            try:
                await context.storage_state(path="fresh_session.json")
                print("✅ 已保存新的会话状态: fresh_session.json")
            except Exception as e:
                print(f"❌ 保存会话状态失败: {e}")
            
            print("\n=== 现在请手动探索 ===")
            print("1. 查看左侧导航菜单")
            print("2. 找到课程、学习、培训等相关菜单")
            print("3. 点击进入，记录URL")
            print("4. 完成后按回车键...")
            
            input()
            
            # 再次检查页面状态
            final_url = page.url
            final_title = await page.title()
            print(f"\n最终页面:")
            print(f"  URL: {final_url}")
            print(f"  标题: {final_title}")
            
            if final_url != current_url:
                print(f"✅ 页面已跳转，新的URL: {final_url}")
                print("请将这个URL告诉我，我会更新配置文件")
            else:
                print("⚠️  页面未发生变化，可能没有找到课程页面")
                
        else:
            print("❌ 未能进入工作台页面")
            print("请检查登录是否成功")
        
        print("\n=== 探索完成 ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(simple_explore())
