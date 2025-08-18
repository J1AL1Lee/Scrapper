#!/usr/bin/env python3
"""
分析工作台页面元素，找到需要点击的用户菜单和个人信息元素
"""
import asyncio
from playwright.async_api import async_playwright
from config import settings

async def find_elements():
    """分析页面元素"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        
        # 使用已保存的会话状态
        context = await browser.new_context(
            storage_state="storage_state.json",
            user_agent=settings.user_agent,
            viewport={"width": settings.viewport[0], "height": settings.viewport[1]},
            locale=settings.locale,
            timezone_id=settings.timezone_id,
        )
        
        page = await context.new_page()
        
        print("=== 分析工作台页面元素 ===")
        
        # 访问工作台页面
        workbench_url = "https://saas.psyyun.com/#/wel/index"
        print(f"访问工作台: {workbench_url}")
        
        await page.goto(workbench_url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        print(f"当前页面: {page.url}")
        print(f"页面标题: {await page.title()}")
        
        print("\n=== 查找所有可见元素 ===")
        
        # 查找所有可见的元素
        visible_elements = page.locator("*:visible")
        count = await visible_elements.count()
        print(f"找到 {count} 个可见元素")
        
        # 分析前50个元素
        user_related_elements = []
        
        for i in range(min(50, count)):
            try:
                element = visible_elements.nth(i)
                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                text_content = await element.inner_text()
                class_attr = await element.get_attribute("class")
                id_attr = await element.get_attribute("id")
                
                # 检查是否包含用户相关信息
                if text_content and any(keyword in text_content.lower() for keyword in 
                                     ['用户', '个人', '头像', '登录', 'logout', 'profile', 'avatar']):
                    user_related_elements.append({
                        'index': i,
                        'tag': tag_name,
                        'text': text_content.strip(),
                        'class': class_attr,
                        'id': id_attr
                    })
                    print(f"🎯 用户相关元素 {i}: {tag_name} - {text_content.strip()}")
                    if class_attr:
                        print(f"    class: {class_attr}")
                    if id_attr:
                        print(f"    id: {id_attr}")
                    print()
                
                # 显示所有元素的基本信息
                if text_content and len(text_content.strip()) < 50:
                    print(f"{i:2d}: {tag_name} - {text_content.strip()}")
                    if class_attr:
                        print(f"     class: {class_attr}")
                    if id_attr:
                        print(f"     id: {id_attr}")
                
            except Exception as e:
                print(f"分析元素 {i} 时出错: {e}")
        
        print(f"\n=== 找到 {len(user_related_elements)} 个用户相关元素 ===")
        
        # 让用户手动操作，找到正确的元素
        print("\n=== 现在请手动操作 ===")
        print("1. 点击用户名下拉菜单")
        print("2. 选择个人信息")
        print("3. 进入课程页面")
        print("4. 完成后按回车键...")
        
        input()
        
        # 检查最终页面
        final_url = page.url
        final_title = await page.title()
        print(f"\n最终页面:")
        print(f"  URL: {final_url}")
        print(f"  标题: {final_title}")
        
        if "/userinfo" in final_url:
            print("✅ 成功进入个人信息页面！")
            print("请告诉我你点击了哪些元素，我会更新爬虫代码")
        else:
            print("⚠️  未能进入个人信息页面")
        
        print("\n=== 分析完成 ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_elements())
