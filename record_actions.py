#!/usr/bin/env python3
"""
录制用户操作流程，自动生成 Playwright 代码
"""
import asyncio
from playwright.async_api import async_playwright
from config import settings

async def record_actions():
    """录制用户操作"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        
        # 创建新的上下文（不使用已保存的会话状态）
        context = await browser.new_context(
            user_agent=settings.user_agent,
            viewport={"width": settings.viewport[0], "height": settings.viewport[1]},
            locale=settings.locale,
            timezone_id=settings.timezone_id,
        )
        
        page = await context.new_page()
        
        print("=== Playwright 操作录制 ===")
        print("1. 脚本会打开浏览器并访问登录页面")
        print("2. 请先完成登录")
        print("3. 登录成功后，按照正常流程操作：")
        print("   - 点击用户名下拉菜单")
        print("   - 选择个人信息")
        print("   - 进入课程页面")
        print("4. 完成后按回车键...")
        
        # 访问登录页面
        print(f"\n正在访问登录页面: {settings.login_url}")
        await page.goto(settings.login_url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        print(f"当前页面: {page.url}")
        print(f"页面标题: {await page.title()}")
        
        # 等待用户登录
        print("\n=== 请先完成登录 ===")
        print("在浏览器中完成登录操作...")
        
        # 等待登录成功
        max_wait_time = 300  # 5分钟
        check_interval = 2
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                current_url = page.url
                current_title = await page.title()
                
                # 检查是否登录成功
                if "/wel/index" in current_url or "工作台" in current_title:
                    print(f"✅ 检测到登录成功！页面已跳转到工作台")
                    print(f"当前URL: {current_url}")
                    print(f"页面标题: {current_title}")
                    break
                
                # 检查是否还在登录页面
                if "/login" in current_url:
                    print(f"仍在登录页面，继续等待... ({elapsed_time}s)")
                else:
                    print(f"页面发生变化: {current_url} - {current_title}")
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
                # 每30秒提示一次
                if elapsed_time % 30 == 0:
                    remaining = max_wait_time - elapsed_time
                    print(f"仍在等待登录... 剩余时间: {remaining}秒")
                    
            except Exception as e:
                print(f"检测过程中出错: {e}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
        
        if elapsed_time >= max_wait_time:
            print("❌ 登录超时，请检查登录是否成功")
            await browser.close()
            return
        
        # 登录成功后，等待页面稳定
        print("\n=== 登录成功，等待页面稳定 ===")
        await asyncio.sleep(5)
        
        # 开始录制
        print("\n=== 开始录制操作 ===")
        print("现在请在浏览器中完成以下操作：")
        print("1. 点击用户名下拉菜单")
        print("2. 选择个人信息")
        print("3. 进入课程页面")
        print("4. 完成后按回车键...")
        
        # 记录初始状态
        initial_url = page.url
        initial_title = await page.title()
        
        # 等待用户操作
        input("完成操作后按回车键继续...")
        
        # 检查最终状态
        final_url = page.url
        final_title = await page.title()
        
        print(f"\n=== 操作结果 ===")
        print(f"初始页面: {initial_url}")
        print(f"初始标题: {initial_title}")
        print(f"最终页面: {final_url}")
        print(f"最终标题: {final_title}")
        
        # 检查是否成功进入个人信息页面（通过URL或标题变化）
        if ("/userinfo" in final_url or 
            "用户中心" in final_title or 
            "个人信息" in final_title or
            final_title != initial_title):
            print("✅ 成功进入个人信息页面！")
            
            # 分析页面变化，生成操作代码
            print("\n=== 生成操作代码 ===")
            await generate_action_code(page, initial_url, final_url)
        else:
            print("⚠️  未能进入个人信息页面")
            print("请检查操作是否正确")
        
        print("\n=== 录制完成 ===")
        await browser.close()

async def generate_action_code(page, initial_url, final_url):
    """生成操作代码"""
    try:
        # 分析页面上的元素，找到可能的点击目标
        print("分析页面元素，生成点击代码...")
        
        # 查找可能的用户菜单元素
        user_menu_candidates = []
        selectors_to_try = [
            ".user-info", ".user-menu", ".user-profile", ".user-avatar",
            ".avatar", ".profile", ".user-name", ".user-account",
            "[class*='user']", "[class*='profile']", "[class*='avatar']",
            ".el-dropdown", ".ant-dropdown", ".dropdown"
        ]
        
        for selector in selectors_to_try:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    element = page.locator(selector).first
                    text = await element.inner_text()
                    class_attr = await element.get_attribute("class")
                    user_menu_candidates.append({
                        'selector': selector,
                        'text': text.strip() if text else '',
                        'class': class_attr
                    })
            except Exception:
                continue
        
        # 查找可能的个人信息菜单项
        personal_info_candidates = []
        personal_selectors = [
            "text=个人信息", "text=个人资料", "text=用户信息", "text=我的信息",
            ".menu-item", ".dropdown-item", ".el-menu-item", ".ant-menu-item"
        ]
        
        for selector in personal_selectors:
            try:
                if selector.startswith("text="):
                    element = page.locator(selector)
                else:
                    element = page.locator(selector)
                
                count = await element.count()
                if count > 0:
                    text = await element.first.inner_text()
                    personal_info_candidates.append({
                        'selector': selector,
                        'text': text.strip() if text else ''
                    })
            except Exception:
                continue
        
        # 生成代码
        print("\n=== 建议的操作代码 ===")
        print("请将以下代码复制到 crawler.py 中：")
        print()
        print("```python")
        print("# 用户菜单选择器（按优先级排序）")
        for i, candidate in enumerate(user_menu_candidates):
            print(f"user_menu_selector_{i+1} = '{candidate['selector']}'  # {candidate['text']} (class: {candidate['class']})")
        
        print()
        print("# 个人信息菜单项选择器（按优先级排序）")
        for i, candidate in enumerate(personal_info_candidates):
            print(f"personal_info_selector_{i+1} = '{candidate['selector']}'  # {candidate['text']}")
        
        print()
        print("# 操作流程")
        print("await page.goto(workbench_url)")
        print("await page.wait_for_load_state('domcontentloaded')")
        print("await page.locator(user_menu_selector_1).click()")
        print("await page.wait_for_timeout(1000)")
        print("await page.locator(personal_info_selector_1).click()")
        print("await page.wait_for_load_state('domcontentloaded')")
        print("```")
        
    except Exception as e:
        print(f"生成代码时出错: {e}")

if __name__ == "__main__":
    asyncio.run(record_actions())
