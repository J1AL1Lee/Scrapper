
import argparse, asyncio
from loguru import logger
from crawler import CourseCrawler

def parse_args():
    p = argparse.ArgumentParser(description="Click-Captcha Course Scraper")
    p.add_argument("--limit", type=int, default=500, help="抓取数量上限")
    p.add_argument("--login-manual", action="store_true", help="手动一次登录并保存会话")
    p.add_argument("--use-solver", choices=["ruokuai", "ocr"], help="选择验证码识别方式 (ruokuai: 若快在线服务, ocr: ddddocr本地识别)")
    return p.parse_args()

async def amain():
    args = parse_args()
    crawler = CourseCrawler(use_solver=args.use_solver)
    await crawler.run(limit=args.limit, manual_login=args.login_manual)

if __name__ == "__main__":
    asyncio.run(amain())
