
import asyncio, random, csv, time
from loguru import logger
from typing import Iterable
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

def jitter_sleep(min_ms: int, max_ms: int):
    delay = random.randint(min_ms, max_ms) / 1000
    return asyncio.sleep(delay)

def export_csv(path: str, rows: Iterable[dict]):
    rows = list(rows)
    if not rows:
        logger.warning("没有可导出的数据")
        return
    keys = sorted({k for r in rows for k in r.keys()})
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    logger.info(f"已导出 {len(rows)} 条到 {path}")

def now_ms() -> int:
    return int(time.time() * 1000)

def random_human_path(width: int, height: int, n: int = 10):
    return [(random.randint(3, width-3), random.randint(3, height-3)) for _ in range(n)]

def retryable():
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        reraise=True
    )
