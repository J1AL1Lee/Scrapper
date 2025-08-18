
from pydantic import BaseModel
import os

class Settings(BaseModel):
    base_url: str = "https://saas.psyyun.com/"
    login_url: str = "https://saas.psyyun.com/#/login?tenantId=8"
    username: str = os.getenv("SCRAPER_USERNAME", "22071120")
    password: str = os.getenv("SCRAPER_PASSWORD", "Bjut#22071120")

    # 课程页面基础URL（不包含动态参数）
    courses_base_url: str = "https://saas.psyyun.com/#/userinfo/index"
    # 工作台页面（用于获取动态参数）
    workbench_url: str = "https://saas.psyyun.com/#/wel/index"
    
    max_concurrency: int = 2
    per_page_limit: int = 50
    request_interval_min_ms: int = 600
    request_interval_max_ms: int = 1600
    
    # 页面加载配置
    page_load_timeout: int = 30000  # 30秒
    element_wait_timeout: int = 15000  # 15秒
    retry_attempts: int = 3
    retry_delay_ms: int = 2000

    http_proxy: str | None = os.getenv("HTTP_PROXY")
    https_proxy: str | None = os.getenv("HTTPS_PROXY")

    solver_provider: str | None = None
    solver_username: str | None = os.getenv("SOLVER_USERNAME")
    solver_password: str | None = os.getenv("SOLVER_PASSWORD")
    solver_soft_id: str | None = os.getenv("SOLVER_SOFT_ID")

    headless: bool = False
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    viewport: tuple[int, int] = (1366, 768)
    timezone_id: str = "Asia/Shanghai"
    locale: str = "zh-CN"
    color_scheme: str = "light"

settings = Settings()
