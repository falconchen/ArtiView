# main.py

# main.py

from typing import Optional


from fastapi import FastAPI, BackgroundTasks, Query, Path, Depends, HTTPException

import hashlib
import redis
#import datetime 
from datetime import datetime,date,timedelta
import time
import json
from fastapi.middleware.cors import CORSMiddleware
import pytz



ONE_DAY_IN_SECONDS = 86400
ONE_WEEK_IN_SECONDS = 604800




app = FastAPI()

# 连接 Redis 数据库
#redis_client = redis.StrictRedis(host='redis', port=6379, db=0)


# 加载配置文件
with open("config.json") as f:
    config = json.load(f)

DEFAULT_TIMEZONE = pytz.timezone(config.get("default_timezone", "Asia/Shanghai"))

# 从配置文件中获取 Redis 配置
redis_config = config['redis']

# 连接 Redis 数据库
redis_client = redis.StrictRedis(
    host=redis_config.get('host','redis'),
    port=redis_config.get('port',6379),
    password=redis_config.get('password',""),
    ssl=redis_config.get('ssl', False),
    db=redis_config.get('db', 0)
)


# 获取配置文件中的 allowed_origins
allowed_origins = config.get("allowed_origins", [])

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=config.get("allow_credentials", False),
    allow_methods=config.get("allow_methods", []),
    allow_headers=config.get("allow_headers", []),
)

# 获取配置文件中的 allowed_site_ids
allowed_site_ids = config.get("allowed_site_ids", {})

# 自定义依赖项函数，用于验证 site_id 是否在允许的范围内
def get_site_id(site_id: str = Path(..., description="网站ID")):
    
    
    secret = allowed_site_ids.get(site_id)
    if not secret: 
        raise HTTPException(status_code=400, detail="无效的site_id")
    return site_id


def get_current_date_str():
    # current_date = datetime.date.today()
    # return current_date.isoformat()
    return datetime.now(DEFAULT_TIMEZONE).strftime('%Y%m%d')

# 文章访问计数器
def increment_article_view_count(site_id: str, article_id: str):
    
    today = get_current_date_str()
    redis_client.incr(f'{site_id}:article:{article_id}:{today}')
    redis_client.incr(f'{site_id}:article:{article_id}:total')


# 网站每日访问计数器
def increment_site_daily_view_count(site_id):
    # 获取当前日期字符串
    current_date_str = get_current_date_str()
    # 拼接每日键名，格式为 "SITE_ID:YYYYMMDD"
    daily_key = f"{site_id}:site:{current_date_str}"
    # 使用 INCR 命令实现自增计数
    redis_client.incr(daily_key)


# 获取文章访问数
def get_article_view_count(site_id:str, article_id:str):
    view_count = redis_client.get(f'{site_id}:article:{article_id}:total')
    return int(view_count) if view_count else 0

# 获取文章指定日期访问数
def get_site_daily_view_count(site_id:str, date_str:str):
    #移除 date_str如2023-08-04的`-`
    date_str = date_str.replace('-','')
    view_count = redis_client.get(f'{site_id}:site:{date_str}')
    return int(view_count) if view_count else 0


# 生成校验键
def generate_validation_key(site_id: str, article_id: str, other: int = 0):
    secret = allowed_site_ids.get(site_id)
    key_string = f"{site_id}{secret}{article_id}{other}"
    return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

# 统计文章访问数，接收GET请求

@app.get("/site/{site_id}/count_article_views/")
async def count_article_views(
    background_tasks: BackgroundTasks,
    site_id: str = Depends(get_site_id),
    article_id: str = Query(..., description="文章ID"),
    publish_timestamp: Optional[int] = Query(
        default=None, description="文章发布时间戳"),
    validation_key: str = Query(...,
                                description="校验键"),
    
):
    # 接下来，检查 publish_timestamp 是否为空
    if publish_timestamp is None:
        # 如果为空，表示该参数未提供，可以根据需要执行相应逻辑
        # 例如，设置默认的发布时间戳
        publish_timestamp = 0

    # 生成预期的校验键
    expected_key = generate_validation_key(
        site_id, article_id, publish_timestamp)

    # 校验键是否匹配
    if validation_key != expected_key:
        raise HTTPException(status_code=400, detail="校验失败：无效的校验键")

    # 增加文章访问数量
    increment_article_view_count(site_id, article_id)
    
    # 增加网站每日访问计数器    
    background_tasks.add_task(increment_site_daily_view_count, site_id)

    # 添加文章到热门列表(仅发布时间一周内)
    current_timestamp = int(time.time())
    expiration_time = publish_timestamp + ONE_WEEK_IN_SECONDS
    if expiration_time > current_timestamp:
        background_tasks.add_task(add_article_to_weekly_hot, site_id, article_id, expiration_time)        
    
    #后台执行任务
    background_tasks.add_task(update_all_ranks, site_id, article_id)
    return {"message": "文章访问数已统计"}


# 添加文章到 weekly_hot  中，设置过期时间
def add_article_to_weekly_hot(site_id, article_id, expiration_time):

    weekly_hot_key = f"{site_id}:weekly_hot:{article_id}"

    # # 获取文章访问量
    # view_count = get_article_view_count(site_id, article_id)
    # print(f"article_id -> {article_id}/{view_count}")
    redis_client.set(weekly_hot_key, expiration_time)

    # 设置文章的过期时间
    return redis_client.expireat(weekly_hot_key, expiration_time)

def calculate_expiry_time(expiry_type: str) -> int:
    now = datetime.now(DEFAULT_TIMEZONE)
    if expiry_type == 'daily':
        tomorrow = now + timedelta(days=1)
        expiry_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0, tzinfo=DEFAULT_TIMEZONE)
    elif expiry_type == 'weekly':
        days_until_next_monday = (7 - now.weekday()) % 7
        next_monday = now + timedelta(days=days_until_next_monday)
        expiry_time = datetime(next_monday.year, next_monday.month, next_monday.day, 0, 0, 0, tzinfo=DEFAULT_TIMEZONE)
    elif expiry_type == 'monthly':
        next_month = now.replace(day=28) + timedelta(days=4)
        first_day_of_next_month = next_month.replace(day=1)
        expiry_time = datetime(first_day_of_next_month.year, first_day_of_next_month.month, first_day_of_next_month.day, 0, 0, 0, tzinfo=DEFAULT_TIMEZONE)
    return int(expiry_time.timestamp())

def update_rank(site_id: str, article_id: str, rank_key: str, expiry_type: str):
    today = datetime.now(DEFAULT_TIMEZONE)
    scores = 0
    
    if expiry_type == 'daily':
        # 日排行榜，计算当天0时起的阅读数
        start_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        key = f'{site_id}:article:{article_id}:{start_day.strftime("%Y%m%d")}'
        scores = int(redis_client.get(key) or 0)
    
    elif expiry_type == 'weekly':
        # 周排行榜，计算从本周周一0时到当前日的阅读数
        start_day = today - timedelta(days=today.weekday())
        for i in range((today - start_day).days + 1):
            day = (start_day + timedelta(days=i)).strftime('%Y%m%d')
            key = f'{site_id}:article:{article_id}:{day}'
            score = int(redis_client.get(key) or 0)
            scores += score

    elif expiry_type == 'monthly':
        # 月排行榜，计算从当月1号0时到当前日的阅读数
        start_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for i in range((today - start_day).days + 1):
            day = (start_day + timedelta(days=i)).strftime('%Y%m%d')
            key = f'{site_id}:article:{article_id}:{day}'
            score = int(redis_client.get(key) or 0)
            scores += score

    

    redis_client.zadd(rank_key, {f'{site_id}:{article_id}': scores})

    # 检查键是否设置了过期时间，若未设置则设置过期时间    
    if redis_client.ttl(rank_key) == -1:
        expiry_time = calculate_expiry_time(expiry_type)
        redis_client.expireat(rank_key, expiry_time)

def update_all_ranks(site_id: str, article_id: str):
    update_rank(site_id, article_id, f'{site_id}:article:rank:daily', 'daily')
    update_rank(site_id, article_id, f'{site_id}:article:rank:weekly', 'weekly')
    update_rank(site_id, article_id, f'{site_id}:article:rank:monthly', 'monthly')

# 生成指定日期的日排行榜
def generate_daily_rank(site_id: str, date: str):
    rank_key = f'{site_id}:article:rank:daily:{date}'
    keys_pattern = f'{site_id}:article:*:{date}'
    keys = redis_client.keys(keys_pattern)

    scores = {}
    for key in keys:
        article_id = key.decode().split(":")[2]
        score = int(redis_client.get(key) or 0)
        scores[f'{site_id}:{article_id}'] = score

    redis_client.zadd(rank_key, scores)

# 获取前多少条数据的 weekly_hot 文章访问量和 ID
@app.get("/site/{site_id}/weekly_hot_articles/")
async def weekly_hot_articles(
        site_id: str = Depends(get_site_id),
        limit: int = Query(10, description="返回文章数，最多10篇")):
    # 拼接 Hash 的键名
    weekly_hot_keys = f"{site_id}:weekly_hot:*"
    # 获取 weekly_hot  中的所有成员
    weekly_hot_members = redis_client.keys(weekly_hot_keys)
    # 获取文章 ID 和对应的 Redis 值（views）并组成新的字典数组
    # 构建要获取的所有文章id对应的keys
    article_keys = [key.replace(b":weekly_hot:", b":article:") + b":total" for key in weekly_hot_members]


    # 使用 redis_client.mget() 一次获取所有文章id对应的访问量数据
    view_counts = redis_client.mget(article_keys)

    # 组装结果
    weekly_hot_articles = [
        {
            "article_id": str(key.decode('utf-8').split(":")[-1]),
            "view_count": int(view_count.decode()) if view_count else 0
        }
        for key, view_count in zip(weekly_hot_members, view_counts)
    ]
    # 根据访问量从大到小排序
    sorted_articles = sorted(
        weekly_hot_articles, key=lambda x: x["view_count"], reverse=True)

    # 返回前多少数据
    return sorted_articles[:limit]


# 获取指定文章ID的总访问数
@app.get("/site/{site_id}/get_article_views/")
async def get_article_views(site_id: str = Depends(get_site_id),
                            article_id: str = Query(..., description="文章ID")):
    view_count = get_article_view_count(site_id, article_id)
    return {"view_count": view_count}


#取站点日访问量
@app.get("/site/{site_id}/get_site_daily_views/")
async def get_site_daily_views(site_id: str = Depends(get_site_id),
                            date_str: str = Query(None, description="日期，格式如2023-08-02或20230802")):
    if date_str is None:
        # 如果 date_str 为空，则使用今日的日期
        today = date.today()
        date_str = today.strftime("%Y%m%d")
    view_count = get_site_daily_view_count(site_id,date_str)
    return {"site_id": site_id, "date_str":date_str, "view_count": view_count}


#取文章排行榜
@app.get("/site/{site_id}/top_articles/{rank_type}/")
def get_top_articles(
    site_id: str = Depends(get_site_id),
    rank_type: str = Path(..., description="Type of rank to retrieve (weekly, daily, monthly)"),    
    limit: int = Query(10, description="返回文章数，默认10篇"),
    date: str = Query(None, description="Date for daily rank in YYYYMMDD format")

):
    
    if rank_type not in ['weekly', 'daily', 'monthly']:
        raise HTTPException(status_code=400, detail="Invalid rank_type. Choose from 'weekly', 'daily', 'monthly'.")
    
    # 如果 rank_type 是 daily 并且指定了日期，则使用该日期
    if rank_type == 'daily' and date:
        try:
            # 验证日期格式
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD.")

        rank_key = f'{site_id}:article:rank:daily:{date}'
        
        # 检查是否存在该日期的排行榜，如果不存在则生成
        if not redis_client.exists(rank_key):
            generate_daily_rank(site_id, date)
    else:
        rank_key = f'{site_id}:article:rank:{rank_type}'

    
    raw_data = redis_client.zrevrange(rank_key, 0, limit-1, withscores=True)
    
    # 处理数据，移除 site_id 前缀并将 score 转换为整数
    processed_data = [
        {"article_id": item.decode().split(":")[1], "view_count": int(score)}
        for item, score in raw_data
    ]
    
    return processed_data



@app.get("/site/{site_id}/debug/get_key/")
async def debug_get_key(
        site_id: str = Depends(get_site_id),
        article_id: str = Query(..., description="待计算的文章id")):
    return {"site_id": site_id, "article_id": article_id, "key": generate_validation_key(site_id, article_id)}


# 新接口：用于开发调试的文章访问计数器，无需提供 validation_key
@app.get("/site/{site_id}/debug/count_article_views/")
async def debug_count_article_views(
        site_id: str = Depends(get_site_id),
        article_id: str = Query(..., description="文章ID")):
    # 增加文章访问数量
    increment_article_view_count(site_id, article_id)
    view_count = get_article_view_count(site_id, article_id)
    return {"site_id": site_id, "article_id": article_id, "view_count": view_count, "message": "文章访问数已统计（开发调试模式）"}


@app.get("/site/{site_id}/debug/count_hot/")
async def debug_count_article_views(
    site_id: str = Depends(get_site_id),
    article_id: str = Query(..., description="文章ID"),
    days: int = Query(..., description="文章发布时间，多少天前发布")
):
    publish_timestamp = int(datetime.now(DEFAULT_TIMEZONE
    ).timestamp()) - days * ONE_DAY_IN_SECONDS  # 假设发布时间在3天前
    validation_key = generate_validation_key(
        site_id, article_id, publish_timestamp)
    return {'site_id': site_id, 'article_id': article_id, 'days': days, 'validation_key': validation_key,
            'url': f"http://localhost:8000/site/{site_id}/count_article_views/?article_id={article_id}&publish_timestamp={publish_timestamp}&validation_key={validation_key}"
            }


# 测试
@app.get("/")
def read_root():
    # 获取当前时间

    current_time = datetime.now(DEFAULT_TIMEZONE)
    return {"app": "ArtiView", "visit_at": current_time.strftime("%Y-%m-%d %H:%M:%S")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
