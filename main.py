
import argparse, asyncio
from loguru import logger
from crawler import CourseCrawler

def parse_args():
    p = argparse.ArgumentParser(description="Click-Captcha Course Scraper")
    p.add_argument("--limit", type=int, default=500, help="抓取数量上限")
    p.add_argument("--login-manual", action="store_true", help="手动一次登录并保存会话")
    p.add_argument("--use-solver", choices=["ruokuai", "ocr"], help="选择验证码识别方式 (ruokuai: 若快在线服务, ocr: ddddocr本地识别)")
    p.add_argument("--batch", action="store_true", help="批量处理用户")
    p.add_argument("--users-file", default="users.txt", help="用户配置文件路径")
    return p.parse_args()

async def process_single_user(crawler, username, password, user_index, total_users):
    """处理单个用户"""
    logger.info(f"[{user_index}/{total_users}] 开始处理用户: {username}")
    
    try:
        # 清除之前的登录状态
        import os
        if os.path.exists("storage_state.json"):
            os.remove("storage_state.json")
            logger.info(f"[{user_index}/{total_users}] 已清除登录状态")
        
        # 设置当前用户的登录信息
        crawler.set_user_credentials(username, password)
        
        # 执行登录和抓取流程
        result = await crawler.run(limit=1, manual_login=False)
        
        logger.info(f"[{user_index}/{total_users}] 用户 {username} 处理完成")
        return {"username": username, "status": "success", "result": result}
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{user_index}/{total_users}] 用户 {username} 处理失败: {error_msg}")
        return {"username": username, "status": "failed", "error": error_msg}

async def batch_process_users(crawler, users_file):
    """批量处理用户"""
    try:
        # 读取用户列表
        with open(users_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        total_users = len(lines)
        logger.info(f"读取到 {total_users} 个用户")
        
        if total_users == 0:
            logger.error("用户配置文件为空")
            return
        
        # 解析用户信息
        users = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                username = parts[0]
                password = parts[1]
                users.append((username, password))
            else:
                logger.warning(f"跳过无效行: {line}")
        
        logger.info(f"有效用户数: {len(users)}")
        
        # 批量处理
        results = []
        for i, (username, password) in enumerate(users, 1):
            result = await process_single_user(crawler, username, password, i, len(users))
            results.append(result)
            
            # 用户间稍作延迟，避免过于频繁
            if i < len(users):
                await asyncio.sleep(2)
        
        # 统计结果
        success_count = sum(1 for r in results if r["status"] == "success")
        failed_count = len(results) - success_count
        
        logger.info(f"批量处理完成！成功: {success_count}, 失败: {failed_count}")
        
        # 保存处理结果
        with open("batch_results.txt", "w", encoding="utf-8") as f:
            f.write(f"批量处理结果 - {asyncio.get_event_loop().time()}\n")
            f.write(f"总用户数: {total_users}\n")
            f.write(f"成功: {success_count}\n")
            f.write(f"失败: {failed_count}\n")
            f.write("-" * 50 + "\n")
            
            for result in results:
                if result["status"] == "success":
                    f.write(f"✅ {result['username']}: 成功\n")
                else:
                    f.write(f"❌ {result['username']}: 失败 - {result['error']}\n")
        
        logger.info("处理结果已保存到 batch_results.txt")
        
    except Exception as e:
        logger.error(f"批量处理过程中出错: {e}")

async def amain():
    args = parse_args()
    crawler = CourseCrawler(use_solver=args.use_solver)
    
    if args.batch:
        await batch_process_users(crawler, args.users_file)
    else:
        await crawler.run(limit=args.limit, manual_login=args.login_manual)

if __name__ == "__main__":
    asyncio.run(amain())
