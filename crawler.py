import asyncio, random
import base64
from typing import Optional, List, Tuple, Dict
from loguru import logger
from playwright.async_api import async_playwright, BrowserContext
from utils import jitter_sleep, export_csv
from config import settings
from project_selectors import SELECTORS
try:
    from captcha.ddddocr_solver import DdddOcrClickCaptchaSolver
    DDOCR_AVAILABLE = True
    logger.info("ddddocr验证码识别器可用")
except Exception as e:
    logger.warning(f"ddddocr验证码识别器不可用: {e}")
    DdddOcrClickCaptchaSolver = None
    DDOCR_AVAILABLE = False

STORAGE_STATE = "storage_state.json"

class CourseCrawler:
    def __init__(self, use_solver: Optional[str] = None):
        self.use_solver = use_solver
        self.solver = None
        # 添加动态设置属性
        self._dynamic_settings = None
        
        if use_solver:
            if use_solver == "ruokuai":
                if not (settings.solver_username and settings.solver_password):
                    raise RuntimeError("请在 config.py 或环境变量中配置若快账号")
                # 这里可以保留若快服务，如果需要的话
                logger.info("若快验证码识别服务暂未实现，将使用ddddocr")
                use_solver = "ocr"
            
            if use_solver == "ocr":
                # 使用ddddocr验证码识别器
                if DDOCR_AVAILABLE and DdddOcrClickCaptchaSolver:
                    self.solver = DdddOcrClickCaptchaSolver()
                    logger.info("使用ddddocr验证码识别服务")
                else:
                    logger.error("ddddocr验证码识别器不可用！")
                    logger.error("可能的原因：")
                    logger.error("1. 未安装ddddocr: pip install ddddocr")
                    logger.error("2. 依赖包未正确安装")
                    logger.info("""
解决方案：
1. 安装ddddocr: pip install ddddocr
2. 安装其他依赖: pip install opencv-python pillow numpy
3. 或者使用 --use-solver ruokuai 选择若快在线服务
                        """)
                    raise RuntimeError("ddddocr识别器不可用，请检查依赖安装")
            else:
                raise RuntimeError(f"未知 solver: {use_solver}")
        else:
            # 默认使用ddddocr识别器
            if DDOCR_AVAILABLE and DdddOcrClickCaptchaSolver:
                self.solver = DdddOcrClickCaptchaSolver()
                logger.info("使用默认ddddocr验证码识别服务")
            else:
                logger.warning("ddddocr识别器不可用，将使用手动验证码模式")
                logger.info("提示：可以使用 --use-solver ocr 选择ddddocr服务")
                self.solver = None

    @property
    def settings(self):
        """返回当前使用的设置，优先使用动态设置"""
        return self._dynamic_settings if self._dynamic_settings else settings

    def set_user_credentials(self, username: str, password: str):
        """动态设置用户凭据"""
        from config import Settings
        # 创建新的设置对象，复制全局设置但覆盖用户名和密码
        self._dynamic_settings = Settings()
        # 复制所有全局设置
        for attr in dir(settings):
            if not attr.startswith('_') and hasattr(settings, attr):
                try:
                    setattr(self._dynamic_settings, attr, getattr(settings, attr))
                except:
                    pass
        # 覆盖用户名和密码
        self._dynamic_settings.username = username
        self._dynamic_settings.password = password
        logger.info(f"已设置动态用户凭据: {username}")

    async def _new_context(self, pw) -> BrowserContext:
        args = ["--disable-blink-features=AutomationControlled"]
        browser = await pw.chromium.launch(headless=self.settings.headless, args=args)
        context = await browser.new_context(
            user_agent=self.settings.user_agent,
            viewport={"width": self.settings.viewport[0], "height": self.settings.viewport[1]},
            locale=self.settings.locale,
            timezone_id=self.settings.timezone_id,
            color_scheme=self.settings.color_scheme,
            proxy={"server": self.settings.http_proxy} if self.settings.http_proxy else None,
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        return context

    async def ensure_login(self, context: BrowserContext, manual: bool = False):
        page = await context.new_page()
        
        # 设置更长的超时时间
        page.set_default_timeout(self.settings.page_load_timeout)
        
        await page.goto(self.settings.login_url, wait_until="networkidle")
        
        # 等待页面完全加载
        logger.info("等待页面完全加载...")
        try:
            # 等待页面加载指示器消失
            loading_sel = SELECTORS.get("page_loading", {}).get("loading_indicator")
            if loading_sel:
                await page.wait_for_selector(loading_sel, state="hidden", timeout=30000)
                logger.info("页面加载完成")
        except Exception as e:
            logger.warning(f"等待页面加载超时: {e}")
        
        # 额外等待确保页面稳定
        await asyncio.sleep(3)
        
        login_sel = SELECTORS["login"]
        
        # 记录登录前的URL和标题
        initial_url = page.url
        initial_title = await page.title()
        logger.info(f"登录前 - URL: {initial_url}, 标题: {initial_title}")
        
        # 已登录检查 - 检查是否已经在工作台页面
        if "/wel/index" in page.url or "工作台" in await page.title():
            logger.info("检测到已在工作台页面，登录状态有效")
            return page

        if manual:
            logger.info("人工登录：请在浏览器中完成登录")
            logger.info("脚本会自动检测登录状态，无需手动恢复")
            
            # 轮询检测登录状态，而不是无限期暂停
            max_wait_time = 300  # 最多等待5分钟
            check_interval = 2   # 每2秒检查一次
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                try:
                    # 检查当前URL和标题
                    current_url = page.url
                    current_title = await page.title()
                    
                    logger.info(f"检测中... URL: {current_url}, 标题: {current_title}")
                    
                    # 检查是否跳转到了工作台页面 - 这是最可靠的登录成功标志
                    if "/wel/index" in current_url or "工作台" in current_title:
                        logger.info("检测到登录成功！页面已跳转到工作台")
                        
                        # 等待页面稳定
                        await asyncio.sleep(3)
                        
                        # 保存会话状态
                        logger.info("正在保存会话状态...")
                        await context.storage_state(path=STORAGE_STATE)
                        logger.info("登录成功，已保存 storage_state.json")
                        return page
                    
                    # 检查是否还在登录页面
                    if "/login" in current_url and "心理健康服务平台" in current_title:
                        logger.info("仍在登录页面，继续等待...")
                        # 不检查DOM元素，避免误判
                    else:
                        # 页面发生了变化，但不确定是否登录成功
                        logger.info(f"页面发生变化: {current_url} - {current_title}")
                        
                        # 只有在明确跳转到工作台时才认为登录成功
                        if "/wel/index" in current_url or "工作台" in current_title:
                            logger.info("确认登录成功！")
                            await asyncio.sleep(3)
                            await context.storage_state(path=STORAGE_STATE)
                            logger.info("登录成功，已保存 storage_state.json")
                            return page
                        else:
                            logger.warning(f"页面变化但未跳转到工作台，可能登录失败或跳转到其他页面")
                    
                    # 等待一段时间再检查
                    await asyncio.sleep(check_interval)
                    elapsed_time += check_interval
                    
                    # 每30秒提示一次
                    if elapsed_time % 30 == 0:
                        remaining = max_wait_time - elapsed_time
                        logger.info(f"仍在等待登录... 剩余时间: {remaining}秒")
                        
                except Exception as e:
                    logger.warning(f"检测过程中出错: {e}")
                    await asyncio.sleep(check_interval)
                    elapsed_time += check_interval
            
            # 超时处理
            logger.error(f"等待登录超时 ({max_wait_time}秒)")
            logger.info("请检查是否真的登录成功，或者调整选择器")
            raise RuntimeError("登录验证超时")

        # 自动化登录
        await page.fill(login_sel["username"], self.settings.username)
        await page.fill(login_sel["password"], self.settings.password)

        # 点击登录按钮（只点一次）
        logger.info("点击登录按钮...")
        submit_btn = page.locator(login_sel["submit"])
        if await submit_btn.count() > 0:
            await submit_btn.click()
            logger.info("登录按钮已点击，等待验证码弹出...")
        else:
            logger.error("未找到登录按钮")
            raise RuntimeError("未找到登录按钮")
        
        # 等待验证码弹出
        await asyncio.sleep(2)
        
        # 处理验证码
        max_captcha_attempts = 5
        for attempt in range(max_captcha_attempts):
            try:
                logger.info(f"验证码处理尝试 {attempt + 1}/{max_captcha_attempts}")
                
                # 检查是否有验证码 - 使用多种选择器尝试，优先选择图片元素
                captcha_selectors = [
                    login_sel["captcha_img"],
                    "img[src*='captcha']",
                    "img[src*='verify']", 
                    ".captcha img",
                    ".verify img",
                    "img[alt*='验证码']",
                    "img[alt*='captcha']"
                ]
                
                captcha_img = None
                for selector in captcha_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            logger.info(f"使用选择器 '{selector}' 检测到 {count} 个验证码图片元素")
                            # 取第一个匹配的图片元素，避免多元素定位器问题
                            captcha_img = elements.first
                            break
                    except Exception as e:
                        logger.debug(f"选择器 '{selector}' 失败: {e}")
                        continue
                
                # 如果上面的选择器都没找到，挨个检查所有图片，找到真正的验证码图片
                if not captcha_img or await captcha_img.count() == 0:
                    try:
                        all_images = page.locator("img")
                        image_count = await all_images.count()
                        # logger.info(f"页面上共有 {image_count} 个图片元素，开始逐个检查...")
                        
                        # 挨个检查每个图片，找到包含汉字的验证码图片
                        for i in range(image_count):
                            try:
                                img = all_images.nth(i)
                                src = await img.get_attribute("src")
                                
                                if src and src.startswith("data:image/") and len(src) > 1000:
                                    # logger.info(f"检查第 {i+1} 个图片 (base64长度: {len(src)})")
                                    
                                    # 获取图片尺寸信息
                                    try:
                                        bbox = await img.bounding_box()
                                        if bbox:
                                            width = bbox["width"]
                                            height = bbox["height"]
                                            # logger.info(f"图片 {i+1} 尺寸: {width}x{height}")
                                            
                                            # 优先选择较大的图片（可能是验证码）
                                            if width > 50 and height > 50:
                                                # 尝试截图并检查内容
                                                try:
                                                    img_bytes = await img.screenshot()
                                                    # logger.info(f"图片 {i+1} 截图成功，大小: {len(img_bytes)} 字节")
                                                    
                                                    # 临时保存图片用于调试
                                                    debug_filename = f"debug_img_{i+1}.png"
                                                    with open(debug_filename, "wb") as f:
                                                        f.write(img_bytes)
                                                    # logger.info(f"图片 {i+1} 已保存为 {debug_filename}")
                                                    
                                                    # 检查这个图片是否包含汉字
                                                    if self.solver and hasattr(self.solver, 'is_available') and self.solver.is_available():
                                                        # 使用OCR快速检查图片内容
                                                        # 测试模式下不传指令，只检查图片是否可识别
                                                        test_result = await self.solver.solve_captcha(img_bytes, "测试模式")
                                                        if test_result and test_result.get("success"):
                                                            logger.info(f"✅ 图片 {i+1} 包含可识别的内容，选择为验证码图片")
                                                            captcha_img = img
                                                            break
                                                        else:
                                                            logger.info(f"❌ 图片 {i+1} OCR识别失败或无内容")
                                                    else:
                                                        # 如果没有OCR，选择最大的图片
                                                        if not captcha_img or (width * height > max_size):
                                                            max_size = width * height
                                                            captcha_img = img
                                                            # logger.info(f"图片 {i+1} 尺寸最大，暂时选择为验证码图片")
                                                
                                                except Exception as e:
                                                    logger.debug(f"图片 {i+1} 截图失败: {e}")
                                                    continue
                                    
                                    except Exception as e:
                                        logger.debug(f"获取图片 {i+1} 尺寸失败: {e}")
                                        continue
                                    
                            except Exception as e:
                                logger.debug(f"检查图片 {i+1} 失败: {e}")
                                continue
                        
                        if captcha_img:
                            logger.info(f"最终选择图片 {captcha_img} 作为验证码图片")
                        else:
                            logger.warning("未找到合适的验证码图片")
                            
                    except Exception as e:
                        # logger.debug(f"逐个检查图片失败: {e}")
                        pass
                
                # 调试：只记录图片数量，不输出具体内容
                try:
                    all_images = page.locator("img")
                    image_count = await all_images.count()
                    logger.debug(f"页面上共有 {image_count} 个图片元素")
                except Exception as e:
                    # logger.debug(f"获取页面图片信息失败: {e}")
                    pass
                
                if captcha_img and await captcha_img.count() > 0:
                    logger.info("检测到点击验证码，开始处理...")
                    
                    # 获取验证码图片
                    captcha_src = await captcha_img.get_attribute("src")
                    if captcha_src:
                        # logger.info(f"验证码图片地址: {captcha_src}")
                        
                        # 获取验证码指令文本 - 使用精确选择器
                        instruction = ""
                        try:
                            # 直接使用最精确的选择器
                            instruction_el = page.locator("span.verify-msg")
                            if await instruction_el.count() > 0:
                                instruction = await instruction_el.first.inner_text()
                                if instruction and any(char in instruction for char in ['点击', '依次', '请']):
                                    logger.info(f"获取到验证码指令: {instruction}")
                        except Exception as e:
                            logger.warning(f"获取验证码指令失败: {e}")
                            # 备用方案：尝试其他选择器
                            for selector in [".verify-tip", ".verify-text", ".captcha-tip", ".verify-msg", ".captcha-text", ".verify-instruction"]:
                                try:
                                    instruction_el = page.locator(selector)
                                    if await instruction_el.count() > 0:
                                        instruction = await instruction_el.first.inner_text()
                                        if instruction and any(char in instruction for char in ['点击', '依次', '请']):
                                            logger.info(f"使用备用选择器 '{selector}' 获取到验证码指令: {instruction}")
                                            break
                                except Exception:
                                    continue
                        
                        if not instruction:
                            # 如果还是没找到，尝试从页面文本中查找
                            try:
                                page_text = await page.inner_text("body")
                                logger.debug(f"页面文本长度: {len(page_text)}")
                                if "请依次点击" in page_text:
                                    # 使用正则表达式提取指令
                                    import re
                                    match = re.search(r"请依次点击【([^】]+)】", page_text)
                                    if match:
                                        instruction = f"请依次点击【{match.group(1)}】"
                                        logger.info(f"从页面文本中提取到验证码指令: {instruction}")
                                    else:
                                        # 尝试其他格式
                                        match = re.search(r'请依次点击"([^"]+)"', page_text)
                                        if match:
                                            instruction = f"请依次点击\"{match.group(1)}\""
                                            logger.info(f"从页面文本中提取到验证码指令: {instruction}")
                            except Exception as e:
                                logger.warning(f"从页面文本提取指令失败: {e}")
                        
                        if not instruction:
                            logger.warning("未能获取到验证码指令，将使用默认处理方式")
                            # 尝试从验证码图片的alt属性或title属性获取
                            try:
                                alt_text = await captcha_img.get_attribute("alt")
                                title_text = await captcha_img.get_attribute("title")
                                if alt_text and any(char in alt_text for char in ['点击', '依次', '请']):
                                    instruction = alt_text
                                    logger.info(f"从图片alt属性获取到验证码指令: {instruction}")
                                elif title_text and any(char in title_text for char in ['点击', '依次', '请']):
                                    instruction = title_text
                                    logger.info(f"从图片title属性获取到验证码指令: {instruction}")
                            except Exception as e:
                                logger.debug(f"从图片属性获取指令失败: {e}")
                        
                        if not instruction:
                            logger.error("完全无法获取验证码指令，OCR识别将失败")
                            # 输出页面HTML用于调试
                            try:
                                page_html = await page.content()
                                logger.error(f"页面HTML长度: {len(page_html)}")
                                # 查找包含"点击"、"依次"等关键词的文本
                                if "点击" in page_html or "依次" in page_html:
                                    logger.error("页面包含验证码相关关键词，但选择器未找到")
                                    # 输出页面文本用于调试
                                    page_text = await page.inner_text("body")
                                    logger.error(f"页面文本: {page_text[:500]}...")
                                else:
                                    logger.error("页面不包含验证码相关关键词")
                            except Exception as e:
                                logger.error(f"输出页面HTML失败: {e}")
                            continue
                        
                        # 使用验证码识别服务
                        if self.solver:
                            try:
                                # 获取验证码图片数据
                                if captcha_src and captcha_src.startswith("data:image/"):
                                    # 提取base64数据
                                    import base64
                                    img_data = captcha_src.split(",")[1]
                                    captcha_bytes = base64.b64decode(img_data)
                                    # logger.info("从base64获取验证码图片数据")
                                else:
                                    # 如果base64获取失败，尝试截图
                                    captcha_bytes = await captcha_img.screenshot()
                                    # logger.info("通过截图获取验证码图片数据")
                                
                                # 调用验证码识别服务
                                logger.info("正在识别点击验证码...")
                                captcha_result = await self.solver.solve_captcha(captcha_bytes, instruction)
                                
                                if captcha_result and captcha_result.get("success"):
                                    # 获取点击坐标
                                    click_points = captcha_result.get("click_points", [])
                                    if isinstance(click_points, list) and len(click_points) > 0:
                                        logger.info(f"验证码识别结果: {len(click_points)} 个点击点")
                                        
                                        # 获取验证码图片的位置和尺寸
                                        bbox = await captcha_img.bounding_box()
                                        if not bbox:
                                            logger.error("未获取到验证码图片尺寸")
                                            continue
                                        
                                        # 依次点击每个坐标
                                        for i, point in enumerate(click_points):
                                            x, y = point['x'], point['y']
                                            try:
                                                # 计算绝对坐标（图片左上角为原点）
                                                abs_x = bbox["x"] + x
                                                abs_y = bbox["y"] + y
                                                
                                                logger.info(f"点击第 {i+1} 个点: ({x}, {y}) -> 绝对坐标 ({abs_x}, {abs_y})")
                                                
                                                # 移动到坐标并点击
                                                await page.mouse.move(abs_x, abs_y)
                                                await page.mouse.down()
                                                await page.mouse.up()
                                                
                                                # 点击间隔
                                                await asyncio.sleep(random.uniform(0.2, 0.5))
                                                
                                            except Exception as e:
                                                logger.error(f"点击第 {i+1} 个点时出错: {e}")
                                                continue
                                        
                                        logger.info("验证码点击完成，等待自动登录...")
                                        
                                        # 等待验证码验证完成和自动登录
                                        await asyncio.sleep(3)
                                        
                                        # 检查是否登录成功
                                        current_url = page.url
                                        current_title = await page.title()
                                        
                                        if "/wel/index" in current_url or "工作台" in current_title:
                                            logger.info("✅ 验证码验证成功，自动登录成功！")
                                            await asyncio.sleep(3)
                                            await context.storage_state(path=STORAGE_STATE)
                                            logger.info("登录成功，已保存 storage_state.json")
                                            return page
                                        
                                        # 如果还没跳转，继续等待
                                        logger.info("验证码点击完成，但页面未跳转，继续等待...")
                                        await asyncio.sleep(5)
                                        
                                        # 再次检查
                                        current_url = page.url
                                        current_title = await page.title()
                                        if "/wel/index" in current_url or "工作台" in current_title:
                                            logger.info("✅ 延迟检测到登录成功！")
                                            await asyncio.sleep(3)
                                            await context.storage_state(path=STORAGE_STATE)
                                            logger.info("登录成功，已保存 storage_state.json")
                                            return page
                                        
                                        # 如果还是失败，可能是验证码错误，继续重试
                                        logger.warning("验证码可能点击错误，准备重试...")
                                        continue
                                        
                                    else:
                                        logger.warning(f"验证码识别结果格式错误: {captcha_result}")
                                        # 刷新验证码
                                        await self._refresh_captcha(page, captcha_img)
                                        continue
                                    
                                elif captcha_result and captcha_result.get("partial_success"):
                                    # 部分识别成功的情况
                                    found_chars = captcha_result.get("found_chars", [])
                                    missing_chars = captcha_result.get("missing_chars", [])
                                    logger.warning(f"验证码部分识别成功: 找到 {found_chars}, 缺少 {missing_chars}")
                                    
                                    # 刷新验证码重新识别
                                    logger.info("点击刷新按钮，重新获取验证码...")
                                    await self._refresh_captcha(page, captcha_img)
                                    continue
                                    
                                else:
                                    logger.warning(f"验证码识别失败: {captcha_result}")
                                    # 刷新验证码
                                    await self._refresh_captcha(page, captcha_img)
                                    continue
                                    
                            except Exception as e:
                                logger.error(f"验证码识别出错: {e}")
                                # 刷新验证码
                                await captcha_img.click()
                                await asyncio.sleep(1)
                                continue
                        else:
                            logger.warning("未配置验证码识别服务，尝试手动处理")
                            # 等待用户手动完成验证码
                            logger.info("请在浏览器中手动完成验证码，脚本将等待...")
                            await asyncio.sleep(15)
                            
                            # 检查是否手动完成
                            current_url = page.url
                            current_title = await page.title()
                            if "/wel/index" in current_url or "工作台" in current_title:
                                logger.info("✅ 手动验证码完成，登录成功！")
                                await asyncio.sleep(3)
                                await context.storage_state(path=STORAGE_STATE)
                                logger.info("登录成功，已保存 storage_state.json")
                                return page
                else:
                    logger.info("未检测到验证码，可能已经自动登录成功")
                    # 检查是否已经登录成功
                    current_url = page.url
                    current_title = await page.title()
                    if "/wel/index" in current_url or "工作台" in current_title:
                        logger.info("✅ 无需验证码，直接登录成功！")
                        await asyncio.sleep(3)
                        await context.storage_state(path=STORAGE_STATE)
                        logger.info("登录成功，已保存 storage_state.json")
                        return page
                    
                    # 如果还没跳转，继续等待
                    logger.info("等待页面跳转...")
                    await asyncio.sleep(5)
                    
                    # 再次检查
                    current_url = page.url
                    current_title = await page.title()
                    if "/wel/index" in current_url or "工作台" in current_title:
                        logger.info("✅ 延迟检测到登录成功！")
                        await asyncio.sleep(3)
                        await context.storage_state(path=STORAGE_STATE)
                        logger.info("登录成功，已保存 storage_state.json")
                        return page
                    
                    # 如果还是失败，继续重试
                    continue
                    
            except Exception as e:
                logger.error(f"验证码处理尝试 {attempt + 1} 出错: {e}")
                if attempt < max_captcha_attempts - 1:
                    logger.info("准备重试...")
                    await asyncio.sleep(2)
                    continue
                else:
                    logger.error("验证码处理重试次数已达上限")
                    break
        
        # 如果自动登录失败，抛出异常
        logger.error("自动登录失败，已达到最大重试次数")
        raise RuntimeError("自动登录失败，请检查账号密码或验证码识别服务")

    async def crawl_courses(self, context: BrowserContext, limit: int = 500):
        page = await context.new_page()
        
        try:
            # 设置更长的超时时间
            page.set_default_timeout(self.settings.page_load_timeout)
            
            # 直接访问工作台页面，不检查状态
            logger.info(f"正在访问工作台页面: {self.settings.workbench_url}")
            await page.goto(self.settings.workbench_url, wait_until="networkidle")
            
            # 等待页面完全加载
            logger.info("等待工作台页面完全加载...")
            await asyncio.sleep(5)  # 增加等待时间
            
            # 检查页面是否还在加载
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
                logger.info("页面DOM加载完成")
            except Exception as e:
                logger.warning(f"等待DOM加载超时: {e}")
            
            # 不检查页面状态，直接开始操作
            logger.info("开始模拟用户操作...")
            
            # 等待页面稳定
            await asyncio.sleep(3)
            
            # 模拟用户操作：点击用户名下拉菜单，选择个人信息
            logger.info("模拟用户操作：查找用户名下拉菜单...")
            
            # 使用录制脚本找到的选择器
            user_menu_selectors = [
                "[class*='user']",  # 用户图标
                ".el-dropdown",     # 下拉菜单
                ".user-info", ".user-menu", ".user-profile", ".user-avatar",
                ".avatar", ".profile", ".user-name", ".user-account"
            ]
            
            user_menu_element = None
            for selector in user_menu_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        logger.info(f"找到可能的用户菜单元素: {selector}")
                        user_menu_element = page.locator(selector).first
                        break
                except Exception:
                    continue
            
            if not user_menu_element:
                logger.warning("未找到用户名下拉菜单，尝试查找页面上的其他元素...")
                
                # 调试：显示页面上的所有可见元素
                await self._debug_page_elements(page)
                
                # 尝试查找任何可能包含用户信息的元素
                fallback_selectors = [
                    "button", "a", ".btn", ".link", "span", "div"
                ]
                
                for selector in fallback_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            logger.info(f"找到 {count} 个 {selector} 元素")
                            
                            # 检查前几个元素的文本内容
                            for i in range(min(5, count)):
                                try:
                                    element = elements.nth(i)
                                    text = await element.inner_text()
                                    if text and any(keyword in text.lower() for keyword in ['用户', '个人', '头像', '登录', 'logout']):
                                        logger.info(f"找到可能的用户相关元素: {text}")
                                        user_menu_element = element
                                        break
                                except Exception:
                                    continue
                            
                            if user_menu_element:
                                break
                    except Exception:
                        continue
            
            if not user_menu_element:
                logger.error("未找到用户名下拉菜单")
                raise RuntimeError("无法找到用户名下拉菜单，无法进入课程页面")
            
            # 点击用户名下拉菜单
            logger.info("点击用户名下拉菜单...")
            await user_menu_element.click()
            
            # 等待下拉菜单完全展开
            logger.info("等待下拉菜单展开...")
            await asyncio.sleep(3)  # 增加等待时间
            
            # 查找并点击"个人信息"菜单项
            logger.info("查找个人信息菜单项...")
            personal_info_selectors = [
                ".el-menu-item",  # 先尝试这个，通常是最准确的
                ".el-dropdown-menu .el-menu-item",  # 下拉菜单中的菜单项
                ".el-dropdown-menu li",  # 下拉菜单中的列表项
                ".dropdown-menu li",  # 通用下拉菜单
                ".menu-item", ".dropdown-item", ".ant-menu-item"
            ]
            
            personal_info_clicked = False
            for selector in personal_info_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        logger.info(f"找到菜单项: {selector}, 数量: {count}")
                        
                        # 遍历所有找到的菜单项，查找包含"个人信息"的
                        for i in range(count):
                            try:
                                element = page.locator(selector).nth(i)
                                text = await element.inner_text()
                                logger.debug(f"菜单项 {i+1}: {text}")
                                
                                if text and any(keyword in text for keyword in ['个人信息', '个人资料', '用户信息', '我的信息']):
                                    logger.info(f"找到个人信息菜单项: {text}")
                                    
                                    # 等待元素完全可见和可交互
                                    try:
                                        await element.wait_for_element_state("visible", timeout=10000)
                                        await element.wait_for_element_state("stable", timeout=5000)
                                    except Exception as e:
                                        logger.warning(f"等待元素状态时出错: {e}")
                                    
                                    # 尝试点击
                                    await element.click()
                                    personal_info_clicked = True
                                    logger.info("已点击个人信息菜单项")
                                    break
                            except Exception as e:
                                logger.debug(f"检查菜单项 {i+1} 时出错: {e}")
                                continue
                        
                        if personal_info_clicked:
                            break
                            
                except Exception as e:
                    logger.debug(f"尝试选择器 {selector} 时出错: {e}")
                    continue
            
            if not personal_info_clicked:
                logger.warning("未找到个人信息菜单项，尝试查找所有可见的菜单项...")
                
                # 等待一下，确保下拉菜单完全展开
                await asyncio.sleep(2)
                
                # 查找所有可见的菜单项
                visible_items = page.locator("*:visible")
                for i in range(min(20, await visible_items.count())):
                    try:
                        item = visible_items.nth(i)
                        text = await item.inner_text()
                        if text and any(keyword in text for keyword in ['个人信息', '个人资料', '用户信息', '我的信息']):
                            logger.info(f"找到个人信息相关文本: {text}")
                            
                            # 确保元素可见和稳定
                            try:
                                await item.wait_for_element_state("visible", timeout=5000)
                                await item.wait_for_element_state("stable", timeout=3000)
                            except Exception as e:
                                logger.warning(f"等待元素状态时出错: {e}")
                            
                            await item.click()
                            personal_info_clicked = True
                            break
                    except Exception:
                        continue
            
            if not personal_info_clicked:
                logger.error("无法找到或点击个人信息菜单项")
                raise RuntimeError("无法进入个人信息页面")
            
            # 等待页面跳转
            logger.info("等待页面跳转到个人信息页面...")
            await asyncio.sleep(5)  # 增加等待时间
            
            # 检查当前页面状态
            current_url = page.url
            current_title = await page.title()
            logger.info(f"个人信息页面 - URL: {current_url}, 标题: {current_title}")
            
            # 检查是否跳转到了错误页面
            if "/tenant-error" in current_url:
                logger.error("个人信息页面访问失败，跳转到了租户错误页面")
                raise RuntimeError("无法访问个人信息页面，请检查权限")
            
            # 检查是否还在登录状态
            if "/login" in current_url:
                logger.error("页面仍然在登录状态，可能登录失败")
                raise RuntimeError("登录状态验证失败")
            
            # 检查是否成功进入个人信息页面（通过URL或标题变化）
            if ("/userinfo" in current_url or 
                "用户中心" in current_title or 
                "个人信息" in current_title):
                logger.info("✅ 成功进入个人信息页面！")
            else:
                logger.warning("页面可能未正确跳转，但继续尝试抓取数据")
            
            # 现在应该已经在个人信息页面了，先抓取组织机构并退出登录
            logger.info("开始爬取组织机构信息...")
            org_info = await self._scrape_organization_info(page)
            if org_info:
                await self._save_org_info_to_file(org_info)
                logger.info("✅ 组织机构信息已保存到记事本")
            logger.info("开始退出登录流程...")
            await self._logout_user(page)
            
            # 退出后结束流程
            return []

            while True:
                # 检查页面是否仍然有效
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception as e:
                    logger.error(f"页面加载状态检查失败: {e}")
                    break
                
                # 空列表判断
                try:
                    if await page.locator(csel["empty_marker"]).count() > 0:
                        logger.info("没有更多数据（空列表标记）"); break
                except Exception:
                    pass

                # 检查课程列表容器
                try:
                    items = page.locator(csel["item"])
                    count = await items.count()
                    logger.info(f"本页课程数: {count}")
                    
                    if count == 0:
                        logger.warning("未找到课程项，可能选择器不匹配")
                        # 尝试查找页面上的其他元素来调试
                        await self._debug_page_elements(page)
                        break
                    
                    for i in range(count):
                        if len(rows) >= limit:
                            logger.info("已达抓取上限"); return rows
                        
                        try:
                            it = items.nth(i)
                            def safe_text(loc):
                                try:
                                    return loc.inner_text()
                                except Exception:
                                    return ""
                            
                            title = (await safe_text(it.locator(csel["title"])) or "").strip()
                            teacher = (await safe_text(it.locator(csel["teacher"])) or "").strip()
                            code = (await safe_text(it.locator(csel["code"])) or "").strip()
                            link = ""
                            try:
                                link = (await it.locator(csel["link"]).get_attribute("href") or "").strip()
                            except Exception:
                                pass
                            
                            if title or teacher or code:  # 至少有一个字段有内容
                                rows.append({"title": title, "teacher": teacher, "code": code, "link": link})
                                logger.debug(f"抓取到课程: {title}")
                            
                        except Exception as e:
                            logger.warning(f"抓取第 {i+1} 个课程时出错: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"获取课程列表时出错: {e}")
                    break

                # 翻页
                try:
                    next_btn = page.locator(csel["next_button"])
                    if await next_btn.count() == 0 or (not await next_btn.is_enabled()):
                        logger.info("未找到下一页或不可点击，结束"); break
                    await next_btn.click()
                    await jitter_sleep(self.settings.request_interval_min_ms, self.settings.request_interval_max_ms)
                except Exception as e:
                    logger.warning(f"翻页时出错: {e}")
                    break

            logger.info(f"总共抓取到 {len(rows)} 个课程")
            return rows
            
        except Exception as e:
            logger.error(f"课程抓取过程中出错: {e}")
            raise
        finally:
            # 确保页面被正确关闭
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"关闭课程页面时出错: {e}")
    
    async def _find_course_url(self, page):
        """在工作台页面查找课程链接"""
        try:
            # 查找包含课程相关关键词的链接
            course_keywords = ['个人信息', 'course', 'study', 'training']
            
            # 查找所有链接
            all_links = page.locator("a")
            link_count = await all_links.count()
            logger.info(f"在工作台页面找到 {link_count} 个链接")
            
            for i in range(link_count):
                try:
                    link = all_links.nth(i)
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    
                    if href and text.strip():
                        # 检查是否包含课程相关关键词
                        is_course_related = any(keyword in text.lower() or keyword in href.lower() for keyword in course_keywords)
                        
                        if is_course_related:
                            logger.info(f"找到课程相关链接: {text.strip()} -> {href}")
                            return href
                            
                except Exception as e:
                    logger.debug(f"检查链接 {i+1} 时出错: {e}")
                    continue
            
            # 如果没有找到明确的课程链接，尝试直接构造URL
            logger.info("未找到明确的课程链接，尝试使用基础URL")
            return self.settings.courses_base_url
            
        except Exception as e:
            logger.error(f"查找课程链接时出错: {e}")
            return None

    async def _debug_page_elements(self, page):
        """调试页面元素，帮助诊断选择器问题"""
        logger.info("=== 页面元素调试信息 ===")
        try:
            # 检查页面基本信息
            title = await page.title()
            url = page.url
            logger.info(f"页面标题: {title}")
            logger.info(f"页面URL: {url}")
            
            # 检查一些常见元素
            common_selectors = ["div", "span", "a", "button", "table", "ul", "li"]
            for selector in common_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        logger.info(f"找到 {count} 个 {selector}")
                        # 显示前几个元素的class
                        for i in range(min(3, count)):
                            try:
                                element = page.locator(selector).nth(i)
                                class_attr = await element.get_attribute("class")
                                if class_attr:
                                    logger.info(f"  {i+1}: class='{class_attr}'")
                            except Exception:
                                pass
                except Exception as e:
                    logger.warning(f"检查 {selector} 时出错: {e}")
                    
        except Exception as e:
            logger.error(f"调试页面元素时出错: {e}")

    async def run(self, limit: int = 500, manual_login: bool = False):
        async with async_playwright() as pw:
            context = await self._new_context(pw)
            
            # 尝试加载历史会话
            import os
            if os.path.exists("storage_state.json"):
                await context.close()
                browser = await pw.chromium.launch(headless=self.settings.headless, args=["--disable-blink-features=AutomationControlled"])
                context = await browser.new_context(storage_state="storage_state.json")
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
                logger.info("已加载历史 storage_state.json")

            try:
                # 登录检查
                login_page = await self.ensure_login(context, manual=manual_login)
                
                # 登录成功后，直接在工作台页面开始操作，不需要重新访问
                if login_page:
                    logger.info("登录成功，直接在工作台页面开始操作")
                    
                    # 直接在当前页面开始课程抓取
                    rows = await self.crawl_courses_from_current_page(login_page, limit=limit)
                    export_csv("courses.csv", rows)
                else:
                    logger.error("登录失败")
                    raise RuntimeError("登录失败")
                
            except Exception as e:
                logger.error(f"运行过程中出错: {e}")
                raise
            finally:
                # 确保资源被正确释放
                try:
                    await context.close()
                except Exception as e:
                    logger.warning(f"关闭上下文时出错: {e}")
    
    async def crawl_courses_from_current_page(self, page, limit: int = 500):
        """从当前页面（工作台页面）开始抓取课程"""
        try:
            logger.info("从当前工作台页面开始操作...")
            
            # 等待页面稳定
            await asyncio.sleep(3)
            
            # 模拟用户操作：点击用户名下拉菜单，选择个人信息
            logger.info("模拟用户操作：查找用户名下拉菜单...")
            
            # 使用录制脚本找到的选择器
            user_menu_selectors = [
                "[class*='user']",  # 用户图标
                ".el-dropdown",     # 下拉菜单
                ".user-info", ".user-menu", ".user-profile", ".user-avatar",
                ".avatar", ".profile", ".user-name", ".user-account"
            ]
            
            user_menu_element = None
            for selector in user_menu_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        logger.info(f"找到可能的用户菜单元素: {selector}")
                        user_menu_element = page.locator(selector).first
                        break
                except Exception:
                    continue
            
            if not user_menu_element:
                logger.warning("未找到用户名下拉菜单，尝试查找页面上的其他元素...")
                
                # 调试：显示页面上的所有可见元素
                await self._debug_page_elements(page)
                
                # 尝试查找任何可能包含用户信息的元素
                fallback_selectors = [
                    "button", "a", ".btn", ".link", "span", "div"
                ]
                
                for selector in fallback_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            logger.info(f"找到 {count} 个 {selector} 元素")
                            
                            # 检查前几个元素的文本内容
                            for i in range(min(5, count)):
                                try:
                                    element = elements.nth(i)
                                    text = await element.inner_text()
                                    if text and any(keyword in text.lower() for keyword in ['用户', '个人', '头像', '登录', 'logout']):
                                        logger.info(f"找到可能的用户相关元素: {text}")
                                        user_menu_element = element
                                        break
                                except Exception:
                                    continue
                            
                            if user_menu_element:
                                break
                    except Exception:
                        continue
            
            if not user_menu_element:
                logger.error("未找到用户名下拉菜单")
                raise RuntimeError("无法找到用户名下拉菜单，无法进入课程页面")
            
            # 点击用户名下拉菜单
            logger.info("点击用户名下拉菜单...")
            await user_menu_element.click()
            
            # 等待下拉菜单完全展开
            logger.info("等待下拉菜单展开...")
            await asyncio.sleep(3)  # 增加等待时间
            
            # 查找并点击"个人信息"菜单项
            logger.info("查找个人信息菜单项...")
            personal_info_selectors = [
                ".el-menu-item",  # 先尝试这个，通常是最准确的
                ".el-dropdown-menu .el-menu-item",  # 下拉菜单中的菜单项
                ".el-dropdown-menu li",  # 下拉菜单中的列表项
                ".dropdown-menu li",  # 通用下拉菜单
                ".menu-item", ".dropdown-item", ".ant-menu-item"
            ]
            
            personal_info_clicked = False
            for selector in personal_info_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        logger.info(f"找到菜单项: {selector}, 数量: {count}")
                        
                        # 遍历所有找到的菜单项，查找包含"个人信息"的
                        for i in range(count):
                            try:
                                element = page.locator(selector).nth(i)
                                text = await element.inner_text()
                                logger.debug(f"菜单项 {i+1}: {text}")
                                
                                if text and any(keyword in text for keyword in ['个人信息', '个人资料', '用户信息', '我的信息']):
                                    logger.info(f"找到个人信息菜单项: {text}")
                                    
                                    # 等待元素完全可见和可交互
                                    try:
                                        await element.wait_for_element_state("visible", timeout=10000)
                                        await element.wait_for_element_state("stable", timeout=5000)
                                    except Exception as e:
                                        logger.warning(f"等待元素状态时出错: {e}")
                                    
                                    # 尝试点击
                                    await element.click()
                                    personal_info_clicked = True
                                    logger.info("已点击个人信息菜单项")
                                    break
                            except Exception as e:
                                logger.debug(f"检查菜单项 {i+1} 时出错: {e}")
                                continue
                        
                        if personal_info_clicked:
                            break
                            
                except Exception as e:
                    logger.debug(f"尝试选择器 {selector} 时出错: {e}")
                    continue
            
            if not personal_info_clicked:
                logger.warning("未找到个人信息菜单项，尝试查找所有可见的菜单项...")
                
                # 等待一下，确保下拉菜单完全展开
                await asyncio.sleep(2)
                
                # 查找所有可见的菜单项
                visible_items = page.locator("*:visible")
                for i in range(min(20, await visible_items.count())):
                    try:
                        item = visible_items.nth(i)
                        text = await item.inner_text()
                        if text and any(keyword in text for keyword in ['个人信息', '个人资料', '用户信息', '我的信息']):
                            logger.info(f"找到个人信息相关文本: {text}")
                            
                            # 确保元素可见和稳定
                            try:
                                await item.wait_for_element_state("visible", timeout=5000)
                                await item.wait_for_element_state("stable", timeout=3000)
                            except Exception as e:
                                logger.warning(f"等待元素状态时出错: {e}")
                            
                            await item.click()
                            personal_info_clicked = True
                            break
                    except Exception:
                        continue
            
            if not personal_info_clicked:
                logger.error("无法找到或点击个人信息菜单项")
                raise RuntimeError("无法进入个人信息页面")
            
            # 等待页面跳转
            logger.info("等待页面跳转到个人信息页面...")
            await asyncio.sleep(5)  # 增加等待时间
            
            # 检查当前页面状态
            current_url = page.url
            current_title = await page.title()
            logger.info(f"个人信息页面 - URL: {current_url}, 标题: {current_title}")
            
            # 检查是否跳转到了错误页面
            if "/tenant-error" in current_url:
                logger.error("个人信息页面访问失败，跳转到了租户错误页面")
                raise RuntimeError("无法访问个人信息页面，请检查权限")
            
            # 检查是否还在登录状态
            if "/login" in current_url:
                logger.error("页面仍然在登录状态，可能登录失败")
                raise RuntimeError("登录状态验证失败")
            
            # 检查是否成功进入个人信息页面（通过URL或标题变化）
            if ("/userinfo" in current_url or 
                "用户中心" in current_title or 
                "个人信息" in current_title):
                logger.info("✅ 成功进入个人信息页面！")
            else:
                logger.warning("页面可能未正确跳转，但继续尝试抓取数据")
            
            # 现在应该已经在个人信息页面了，先抓取组织机构并退出登录
            logger.info("开始爬取组织机构信息...")
            org_info = await self._scrape_organization_info(page)
            if org_info:
                await self._save_org_info_to_file(org_info)
                logger.info("✅ 组织机构信息已保存到记事本")
            logger.info("开始退出登录流程...")
            await self._logout_user(page)
            
            # 退出后结束流程
            return []

            while True:
                # 检查页面是否仍然有效
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception as e:
                    logger.error(f"页面加载状态检查失败: {e}")
                    break
                
                # 空列表判断
                try:
                    if await page.locator(csel["empty_marker"]).count() > 0:
                        logger.info("没有更多数据（空列表标记）"); break
                except Exception:
                    pass

                # 检查课程列表容器
                try:
                    items = page.locator(csel["item"])
                    count = await items.count()
                    logger.info(f"本页课程数: {count}")
                    
                    if count == 0:
                        logger.warning("未找到课程项，可能选择器不匹配")
                        # 尝试查找页面上的其他元素来调试
                        await self._debug_page_elements(page)
                        break
                    
                    for i in range(count):
                        if len(rows) >= limit:
                            logger.info("已达抓取上限"); return rows
                        
                        try:
                            it = items.nth(i)
                            def safe_text(loc):
                                try:
                                    return loc.inner_text()
                                except Exception:
                                    return ""
                            
                            title = (await safe_text(it.locator(csel["title"])) or "").strip()
                            teacher = (await safe_text(it.locator(csel["teacher"])) or "").strip()
                            code = (await safe_text(it.locator(csel["code"])) or "").strip()
                            link = ""
                            try:
                                link = (await it.locator(csel["link"]).get_attribute("href") or "").strip()
                            except Exception:
                                pass
                            
                            if title or teacher or code:  # 至少有一个字段有内容
                                rows.append({"title": title, "teacher": teacher, "code": code, "link": link})
                                logger.debug(f"抓取到课程: {title}")
                            
                        except Exception as e:
                            logger.warning(f"抓取第 {i+1} 个课程时出错: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"获取课程列表时出错: {e}")
                    break

                # 翻页
                try:
                    next_btn = page.locator(csel["next_button"])
                    if await next_btn.count() == 0 or (not await next_btn.is_enabled()):
                        logger.info("未找到下一页或不可点击，结束"); break
                    await next_btn.click()
                    await jitter_sleep(self.settings.request_interval_min_ms, self.settings.request_interval_max_ms)
                except Exception as e:
                    logger.warning(f"翻页时出错: {e}")
                    break

            logger.info(f"总共抓取到 {len(rows)} 个课程")
            return rows
            
        except Exception as e:
            logger.error(f"课程抓取过程中出错: {e}")
            raise

    async def _handle_captcha_enhanced(self, page, captcha_img, instruction: str, attempt: int):
        """增强的验证码处理方法"""
        try:
            logger.info(f"开始处理验证码 (尝试 {attempt}/5)")
            
            # 确保验证码图片完全加载
            await asyncio.sleep(2)
            
            # 获取验证码图片数据 - 优化获取方式
            captcha_bytes = None
            captcha_src = None
            
            try:
                # 方法1: 从src属性获取base64数据
                captcha_src = await captcha_img.get_attribute("src")
                if captcha_src and captcha_src.startswith("data:image/"):
                    img_data = captcha_src.split(",")[1]
                    captcha_bytes = base64.b64decode(img_data)
                    logger.info("从base64获取验证码图片数据")
                else:
                    raise Exception("非base64格式")
                    
            except Exception:
                try:
                    # 方法2: 直接截图验证码区域
                    captcha_bytes = await captcha_img.screenshot()
                    logger.info("通过截图获取验证码图片数据")
                except Exception as e:
                    logger.error(f"获取验证码图片数据失败: {e}")
                    return False
            
            if not captcha_bytes:
                logger.error("无法获取验证码图片数据")
                return False
            
            # 保存验证码图片用于调试
            try:
                with open(f"captcha_debug_{attempt}.png", "wb") as f:
                    f.write(captcha_bytes)
                # logger.info(f"验证码图片已保存为 captcha_debug_{attempt}.png")
            except Exception as e:
                logger.debug(f"保存调试图片失败: {e}")
            
            # 使用验证码识别服务
            if self.solver and hasattr(self.solver, 'is_available') and self.solver.is_available():
                logger.info("正在使用OCR识别点击验证码...")
                captcha_result = await self.solver.solve_captcha(captcha_bytes, instruction)
                
                if captcha_result and captcha_result.get("success"):
                    click_points = captcha_result.get("click_points", [])
                    if isinstance(click_points, list) and len(click_points) > 0:
                        logger.info(f"验证码识别成功: {len(click_points)} 个点击点")
                        
                        # 执行点击操作
                        success = await self._execute_clicks(page, captcha_img, click_points)
                        if success:
                            return await self._wait_for_login_success(page)
                        else:
                            logger.warning("点击执行失败")
                            return False
                    else:
                        logger.warning(f"验证码识别结果格式错误: {captcha_result}")
                        return False
                else:
                    error_msg = captcha_result.get("error", "未知错误") if captcha_result else "识别服务无响应"
                    logger.warning(f"验证码识别失败: {error_msg}")
                    return False
            else:
                logger.warning("OCR验证码识别服务不可用，切换到手动模式")
                return await self._handle_manual_captcha(page, instruction)
                
        except Exception as e:
            logger.error(f"验证码处理出错: {e}")
            return False

    async def _execute_clicks(self, page, captcha_img, click_points: List[Dict]) -> bool:
        """执行验证码点击操作"""
        try:
            # 获取验证码图片的边界框
            bbox = await captcha_img.bounding_box()
            if not bbox:
                logger.error("无法获取验证码图片边界框")
                return False
            
            logger.info(f"验证码图片边界框: {bbox}")
            
            # 依次点击每个坐标
            for i, point in enumerate(click_points):
                x, y = point['x'], point['y']
                try:
                    # 计算绝对坐标
                    abs_x = bbox["x"] + x
                    abs_y = bbox["y"] + y
                    
                    logger.info(f"点击第 {i+1} 个点: 相对坐标({x}, {y}) -> 绝对坐标({abs_x}, {abs_y})")
                    
                    # 确保坐标在合理范围内
                    if (abs_x < bbox["x"] or abs_x > bbox["x"] + bbox["width"] or
                        abs_y < bbox["y"] or abs_y > bbox["y"] + bbox["height"]):
                        logger.warning(f"点击坐标超出验证码图片范围，跳过")
                        continue
                    
                    # 执行点击
                    await page.mouse.move(abs_x, abs_y)
                    await asyncio.sleep(0.1)  # 短暂停顿
                    await page.mouse.click(abs_x, abs_y)
                    
                    # 点击间隔
                    click_delay = random.uniform(0.3, 0.7)
                    logger.debug(f"点击完成，等待 {click_delay:.2f} 秒")
                    await asyncio.sleep(click_delay)
                    
                except Exception as e:
                    logger.error(f"点击第 {i+1} 个点时出错: {e}")
                    continue
            
            logger.info("所有点击操作已完成")
            return True
            
        except Exception as e:
            logger.error(f"执行点击操作失败: {e}")
            return False

    async def _wait_for_login_success(self, page, timeout: int = 10) -> bool:
        """等待登录成功"""
        try:
            logger.info("等待验证码验证和自动登录...")
            
            start_time = asyncio.get_event_loop().time()
            check_interval = 0.5
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    current_url = page.url
                    current_title = await page.title()
                    
                    # 检查是否登录成功
                    if "/wel/index" in current_url or "工作台" in current_title:
                        logger.info("✅ 验证码验证成功，自动登录成功！")
                        return True
                    
                    # 检查是否还在验证码页面
                    if "/login" in current_url:
                        # 检查验证码是否还存在
                        captcha_exists = await page.locator("img[src*='captcha'], img[src*='verify'], .captcha img, .verify img").count() > 0
                        if not captcha_exists:
                            # 验证码消失了，可能正在处理
                            logger.info("验证码已消失，继续等待...")
                    
                    await asyncio.sleep(check_interval)
                    
                except Exception as e:
                    logger.debug(f"检查登录状态时出错: {e}")
                    await asyncio.sleep(check_interval)
            
            logger.warning(f"等待登录超时 ({timeout}秒)")
            return False
        except Exception as e:
            logger.error(f"等待登录成功过程中出错: {e}")
            return False

    async def _refresh_captcha(self, page, captcha_img):
        """刷新验证码"""
        try:
            # 获取验证码图片的边界框
            bbox = await captcha_img.bounding_box()
            if not bbox:
                logger.error("无法获取验证码图片边界框")
                return False
            
            # 计算刷新按钮的大致位置（右上角区域）
            # 刷新按钮通常在验证码图片的右上角，稍微偏移一点
            refresh_x = bbox["x"] + bbox["width"] - 30  # 距离右边缘30像素
            refresh_y = bbox["y"] + 30  # 距离上边缘30像素
            
            logger.info(f"点击刷新按钮位置: ({refresh_x}, {refresh_y})")
            
            # 点击刷新按钮
            await page.mouse.move(refresh_x, refresh_y)
            await asyncio.sleep(0.2)
            await page.mouse.click(refresh_x, refresh_y)
            
            # 等待验证码刷新
            logger.info("等待验证码刷新...")
            await asyncio.sleep(2)
            
            # 等待新的验证码图片加载
            try:
                # 等待验证码图片重新加载
                await page.wait_for_selector("img[src*='captcha'], img[src*='verify'], .captcha img, .verify img", 
                                          state="visible", timeout=5000)
                logger.info("验证码刷新成功")
                return True
            except Exception as e:
                logger.warning(f"等待验证码刷新超时: {e}")
                return False
                
        except Exception as e:
            logger.error(f"刷新验证码时出错: {e}")
            return False

    async def _handle_manual_captcha(self, page, instruction: str) -> bool:
        """手动验证码处理"""
        try:
            logger.info("=== 手动验证码模式 ===")
            logger.info(f"验证码指令: {instruction}")
            logger.info("请在浏览器中手动完成验证码")
            logger.info("脚本将自动检测登录状态...")
            
            # 等待用户手动完成验证码，最多等待60秒
            return await self._wait_for_login_success(page, timeout=60)
            
        except Exception as e:
            logger.error(f"手动验证码处理出错: {e}")
            return False



    async def _find_captcha_image(self, page):
        """查找验证码图片元素"""
        try:
            # 多种验证码图片选择器
            captcha_selectors = [
                "img[src*='captcha']",
                "img[src*='verify']", 
                ".captcha img",
                ".verify img",
                "img[alt*='验证码']",
                "img[alt*='captcha']",
                "[class*='captcha'] img",
                "[class*='verify'] img"
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_img = page.locator(selector)
                    count = await captcha_img.count()
                    if count > 0:
                        logger.info(f"使用选择器 '{selector}' 找到验证码图片")
                        return captcha_img.first
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 失败: {e}")
                    continue
            
            # 通过base64特征查找
            all_images = page.locator("img")
            image_count = await all_images.count()
            logger.info(f"页面共有 {image_count} 个图片元素")
            
            for i in range(image_count):
                try:
                    img = all_images.nth(i)
                    src = await img.get_attribute("src")
                    if src and src.startswith("data:image/") and len(src) > 1000:
                        # 检查是否可能是验证码
                        if len(src) > 5000:  # 验证码图片通常较大
                            logger.info(f"通过base64特征找到可能的验证码图片")
                            return img
                except Exception as e:
                    logger.debug(f"检查图片 {i+1} 失败: {e}")
                    continue
            
            logger.warning("未找到验证码图片")
            return None
            
        except Exception as e:
            logger.error(f"查找验证码图片失败: {e}")
            return None

    async def _get_captcha_instruction(self, page):
        """获取验证码指令文本"""
        try:
            instruction = ""
            
            # 精确选择器
            instruction_selectors = [
                "span.verify-msg",
                ".verify-tip", 
                ".verify-text", 
                ".captcha-tip",
                ".captcha-instruction",
                ".verify-instruction"
            ]
            
            for selector in instruction_selectors:
                try:
                    instruction_el = page.locator(selector)
                    if await instruction_el.count() > 0:
                        text = await instruction_el.first.inner_text()
                        if text and any(keyword in text for keyword in ['点击', '依次', '请', '按顺序']):
                            instruction = text.strip()
                            logger.info(f"使用选择器 '{selector}' 获取验证码指令: {instruction}")
                            return instruction
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 失败: {e}")
                    continue
            
            # 从页面文本中提取
            try:
                page_text = await page.inner_text("body")
                if "请依次点击" in page_text:
                    import re
                    patterns = [
                        r"请依次点击【([^】]+)】",
                        r"请依次点击\"([^\"]+)\"",
                        r"请依次点击：([^\s\n]+)",
                        r"请依次点击([^\s\n，。！？]+)"
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, page_text)
                        if match:
                            instruction = match.group(0)
                            logger.info(f"从页面文本提取验证码指令: {instruction}")
                            return instruction
            except Exception as e:
                logger.debug(f"从页面文本提取指令失败: {e}")
            
            # 查找包含指令的任何文本元素
            try:
                text_elements = page.locator("span, div, p, label")
                count = await text_elements.count()
                
                for i in range(min(50, count)):  # 只检查前50个元素
                    try:
                        element = text_elements.nth(i)
                        text = await element.inner_text()
                        if text and any(keyword in text for keyword in ['点击', '依次', '请', '按顺序']):
                            # 进一步验证是否是验证码指令
                            if any(char in text for char in ['【', '】', '"', '"', '汉字', '文字']):
                                instruction = text.strip()
                                logger.info(f"从文本元素提取验证码指令: {instruction}")
                                return instruction
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"从页面文本提取指令失败: {e}")
            
            logger.warning("未能获取验证码指令")
            return ""
            
        except Exception as e:
            logger.error(f"获取验证码指令失败: {e}")
            return ""

    async def _scrape_organization_info(self, page):
        """爬取组织机构信息"""
        try:
            logger.info("开始爬取组织机构信息...")
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            org_info = {}
            
            # 查找用户名 - 用你给的选择器
            try:
                username_el = page.locator("p[data-v-2a389681]")
                if await username_el.count() > 0:
                    username = await username_el.first.inner_text()
                    if username and username.strip():
                        org_info['username'] = username.strip()
                        logger.info(f"找到用户名: {username.strip()}")
                    else:
                        org_info['username'] = self.settings.username
                        logger.info(f"使用配置文件中的用户名: {self.settings.username}")
                else:
                    org_info['username'] = self.settings.username
                    logger.info(f"未找到用户名元素，使用配置文件中的用户名: {self.settings.username}")
            except Exception as e:
                logger.warning(f"获取用户名失败: {e}")
                org_info['username'] = self.settings.username
            
            # 查找组织机构 - 用你给的选择器
            try:
                org_el = page.locator("input.el-input__inner[placeholder='请选择组织机构']")
                if await org_el.count() > 0:
                    # 直接读取输入框值
                    try:
                        org_value = await org_el.input_value()
                    except Exception:
                        org_value = await org_el.get_attribute("value")
                    if org_value and org_value.strip():
                        org_info['organization'] = org_value.strip()
                        logger.info(f"找到组织机构: {org_value.strip()}")
                    else:
                        org_info['organization'] = "心理健康服务平台"
                        logger.info("组织机构字段为空，使用默认值")
                else:
                    org_info['organization'] = "心理健康服务平台"
                    logger.info("未找到组织机构元素，使用默认值")
            except Exception as e:
                logger.warning(f"获取组织机构失败: {e}")
                org_info['organization'] = "心理健康服务平台"
            
            logger.info(f"爬取到的组织机构信息: {org_info}")

            
             # 查找校园id - 用你给的选择器
            try:
                id_el = page.locator("input.el-input__inner[placeholder='请输入身份证号码']")
                if await id_el.count() > 0:
                    # 直接读取输入框值
                    try:
                        id_value = await id_el.input_value()
                    except Exception:
                        id_value = await id_el.get_attribute("value")
                    if id_value and id_value.strip():
                        org_info['studentid'] = id_value.strip()
                        logger.info(f"找到学生id: {id_value.strip()}")
                    else:
                        org_info['studentid'] = "未填写"
                        logger.info("学生id字段为空，使用默认值")
                else:
                    org_info['studentid'] = "未填写"
                    logger.info("未找到组织机构元素，使用默认值")
            except Exception as e:
                logger.warning(f"获取学生id失败: {e}")
                org_info['studentid'] = "未填写"
            
            logger.info(f"爬取到的组织机构信息: {org_info}")
            return org_info

            
        except Exception as e:
            logger.error(f"爬取组织机构信息失败: {e}")
            return None

    async def _save_org_info_to_file(self, org_info):
        """按"用户名 组织机构"单行格式追加到 org_info.txt"""
        try:
            line = f"{org_info.get('username', '未知')} {self.settings.username} {org_info.get('organization', '未知')} {org_info.get('studentid', '未知')}\n"
            with open("org_info.txt", 'a', encoding='utf-8') as f:
                f.write(line)
            logger.info("已写入 org_info.txt 一行记录")
            return "org_info.txt"
        except Exception as e:
            logger.error(f"保存组织机构信息到文件失败: {e}")
            return None

    async def _logout_user(self, page):
        """退出登录"""
        try:
            logger.info("开始退出登录流程...")
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 查找右上角用户菜单 - 用你给的选择器
            user_menu_selector = "span.el-dropdown-link.el-dropdown-selfdefine"
            try:
                user_menu_element = page.locator(user_menu_selector)
                if await user_menu_element.count() == 0:
                    logger.error("未找到用户菜单元素")
                    return False
                
                logger.info("找到用户菜单元素，准备点击...")
                await user_menu_element.first.click()
                
                # 等待下拉菜单展开
                logger.info("等待下拉菜单展开...")
                await asyncio.sleep(3)
                
                # 查找"退出系统"菜单项
                logout_selector = "li:has-text('退出系统')"
                try:
                    logout_element = page.locator(logout_selector)
                    if await logout_element.count() > 0:
                        logger.info("找到退出系统菜单项，准备点击...")
                        await logout_element.first.click()
                        
                        # 等待确认弹窗出现并点击"确定"按钮
                        try:
                            confirm_btn = page.locator("button.el-button.el-button--default.el-button--small.el-button--primary")
                            if await confirm_btn.count() > 0:
                                await confirm_btn.first.click()
                                logger.info("已点击确认退出按钮")
                            else:
                                logger.warning("未找到确认退出按钮")
                        except Exception as e:
                            logger.warning(f"点击确认退出按钮失败: {e}")

                        # 等待跳回登录页
                        for _ in range(10):
                            await asyncio.sleep(1)
                            current_url = page.url
                            if "/login" in current_url:
                                logger.info("✅ 退出登录成功！")
                                return True
                        logger.warning(f"可能退出登录失败，当前URL: {current_url}")
                        return False
                    else:
                        logger.error("未找到退出系统菜单项")
                        return False
                        
                except Exception as e:
                    logger.error(f"点击退出系统菜单项失败: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"点击用户菜单失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"退出登录过程中出错: {e}")
            return False
