# main.py

# main.py

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
import hashlib
import redis
import datetime
import time

ONE_DAY_IN_SECONDS = 86400
ONE_WEEK_IN_SECONDS = 604800
SITE_ID = "bkb"

app = FastAPI()

# 连接 Redis 数据库
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)



def get_current_date_str():
    current_date = datetime.date.today()
    return current_date.isoformat()

# 文章访问计数器


def increment_article_view_count(article_id):
    redis_client.incr(f'{SITE_ID}:article:{article_id}')


# 网站每日访问计数器
def increment_site_daily_view_count():
    # 获取当前日期字符串
    current_date_str = get_current_date_str()
    # 拼接每日键名，格式为 "SITE_ID:YYYY-MM-DD"
    daily_key = f"{SITE_ID}:site:{current_date_str}"
    # 使用 INCR 命令实现自增计数
    redis_client.incr(daily_key)


# 获取文章访问数
def get_article_view_count(article_id):
    view_count = redis_client.get(f'{SITE_ID}:article:{article_id}')
    return int(view_count) if view_count else 0


# 生成校验键
def generate_validation_key(article_id, publish_timestamp=0):
    key_string = SITE_ID + str(article_id) + "_" + str(publish_timestamp)
    return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

# 统计文章访问数，接收GET请求


@app.get("/count_article_views/")
async def count_article_views(article_id: int = Query(..., description="文章ID"),
                              publish_timestamp: Optional[int] = Query(
                                  default=None, description="文章发布时间戳"),
                              validation_key: str = Query(...,
                                                          description="校验键")
                              ):
    # 接下来，检查 publish_timestamp 是否为空
    if publish_timestamp is None:
        # 如果为空，表示该参数未提供，可以根据需要执行相应逻辑
        # 例如，设置默认的发布时间戳
        publish_timestamp = 0

    # 生成预期的校验键
    expected_key = generate_validation_key(article_id, publish_timestamp)

    # 校验键是否匹配
    if validation_key != expected_key:
        raise HTTPException(status_code=400, detail="校验失败：无效的校验键")

    # 增加文章访问数量
    increment_article_view_count(article_id)
    # 增加网站每日访问计数器
    increment_site_daily_view_count()
    # 添加文章到热门列表
    # 获取当前时间戳
    current_timestamp = int(time.time())
    expiration_time = publish_timestamp + ONE_WEEK_IN_SECONDS
    if expiration_time > current_timestamp:
        add_article_to_weekly_hot(article_id, expiration_time)
    return {"message": "文章访问数已统计"}


# 添加文章到 weekly_hot  中，设置过期时间
def add_article_to_weekly_hot(article_id, expiration_time):

    weekly_hot_key = f"{SITE_ID}:weekly_hot:{article_id}"

    # 获取文章访问量
    view_count = get_article_view_count(article_id)
    print(f"article_id -> {article_id}/{view_count}")
    redis_client.set(weekly_hot_key, view_count)

    # 设置文章的过期时间
    return redis_client.expireat(weekly_hot_key, expiration_time)


# 获取前多少条数据的 weekly_hot 文章访问量和 ID
@app.get("/weekly_hot_articles/")
async def weekly_hot_articles(limit: int = Query(10, description="返回文章数，最多10篇")):
    # 拼接 Hash 的键名
    weekly_hot_keys = f"{SITE_ID}:weekly_hot:*"
    print(weekly_hot_keys)
    # 获取 weekly_hot  中的所有成员
    weekly_hot_members = redis_client.keys(weekly_hot_keys)
    # 获取文章 ID 和对应的 Redis 值（views）并组成新的字典数组
    weekly_hot_articles = [{"id": int(key.decode(
        'utf-8').split(":")[-1]), "view_count": int(redis_client.get(key))} for key in weekly_hot_members]

    # 根据访问量从大到小排序
    sorted_articles = sorted(weekly_hot_articles, key=lambda x: x["view_count"], reverse=True)

    # 返回前多少数据
    return sorted_articles[:limit]


# 接口2：获取指定文章ID的总访问数
@app.get("/get_article_views/")
async def get_article_views(article_id: int = Query(..., description="文章ID")):
    view_count = get_article_view_count(article_id)
    return {"article_id": article_id, "view_count": view_count}


@app.get("/get_key/")
async def get_key(id: str = Query(..., description="待计算的文章id")):
    return {"id": id, "key": generate_validation_key(id)}


# 新接口：用于开发调试的文章访问计数器，无需提供 validation_key
@app.get("/debug_count_article_views/")
async def debug_count_article_views(article_id: int = Query(..., description="文章ID")):
    # 增加文章访问数量
    increment_article_view_count(article_id)
    view_count = get_article_view_count(article_id)
    return {"article_id": article_id, "view_count": view_count, "message": "文章访问数已统计（开发调试模式）"}


@app.get("/debug_count_hot/")
async def debug_count_article_views(article_id: int = Query(..., description="文章ID"),
                                    days: int = Query(..., description="多少天前")
                                    ):
    publish_timestamp = int(datetime.datetime.now(
    ).timestamp()) - days * ONE_DAY_IN_SECONDS  # 假设发布时间在3天前
    validation_key = generate_validation_key(article_id, publish_timestamp)
    return {'article_id': article_id, 'days': days, 'validation_key': validation_key,
            'url': f"http://localhost:8000/count_article_views/?article_id={article_id}&publish_timestamp={publish_timestamp}&validation_key={validation_key}"
            }


# 测试
@app.get("/")
def read_root():
    # 获取当前时间
    
    current_time = datetime.datetime.now()
    return {"app": "ArtiView", "visit_at": current_time.strftime("%Y-%m-%d %H:%M:%S")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
