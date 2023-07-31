# main.py

# main.py

from fastapi import FastAPI, HTTPException, Query
import hashlib
import redis
from datetime import datetime, timedelta


app = FastAPI()

# 连接 Redis 数据库
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

# 文章访问计数器
def increment_article_view_count(article_id):
    redis_client.incr(f'article:{article_id}:views')
  

# 获取文章访问数量
def get_article_view_count(article_id):
    view_count = redis_client.get(f'article:{article_id}:views')
    return int(view_count) if view_count else 0

# 添加文章到热门列表
def add_article_to_popular_list(article_id, view_count, time_period):
    redis_client.zadd(f'popular:{time_period}', {article_id: view_count})

# 获取热门文章列表
def get_popular_articles(time_period, limit=10):
    return redis_client.zrevrange(f'popular:{time_period}', 0, limit - 1, withscores=True)

# 生成校验键
def generate_validation_key(article_id):
    key_string = "bkb_" + str(article_id)
    return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

# 修改接口：统计文章访问数，接收GET请求
@app.get("/count_article_views/")
async def count_article_views(article_id: int = Query(..., description="文章ID"),
                              validation_key: str = Query(..., description="校验键")):
    # 生成预期的校验键
    expected_key = generate_validation_key(article_id)

    # 校验键是否匹配
    if validation_key != expected_key:
        raise HTTPException(status_code=400, detail="校验失败：无效的校验键")

    # 增加文章访问数量
    increment_article_view_count(article_id)
    return {"message": "文章访问数已统计"}


# 接口2：获取指定文章ID的总访问数
@app.get("/get_article_views/")
async def get_article_views(article_id: int = Query(..., description="文章ID")):
    view_count = get_article_view_count(article_id)
    return {"article_id": article_id, "view_count": view_count}

@app.get("/get_key/")
async def get_key(id: str = Query(..., description="待计算的文章id")):
    return {"id": id, "key": generate_validation_key(id)}
    



# 新接口：获取文章ID和访问量数据，文章ID大于等于指定文章ID的指定篇数，按访问量从大到小排列，用于获得本周访问数
@app.get("/get_articles_by_id/")
async def get_articles_by_id(article_id: int = Query(..., description="文章ID"),
                             num_articles: int = Query(10, description="返回文章数，最多10篇")):
    articles_data = []

    # 获取 Redis 中文章ID大于等于指定文章ID的指定篇数的文章ID和访问量数据
    keys = redis_client.scan_iter(f'article:{article_id}*')
    for key in keys:
        current_article_id = int(key.split(b':')[1])
        view_count = get_article_view_count(current_article_id)
        articles_data.append({"article_id": current_article_id, "view_count": view_count})

    # 按访问量从大到小排列
    articles_data.sort(key=lambda x: x["view_count"], reverse=True)

    return articles_data[:num_articles]

# 新接口：用于开发调试的文章访问计数器，无需提供 validation_key
@app.get("/debug_count_article_views/")
async def debug_count_article_views(article_id: int = Query(..., description="文章ID")):
    # 增加文章访问数量
    increment_article_view_count(article_id)
    view_count = get_article_view_count(article_id)
    return {"article_id": article_id, "view_count": view_count, "message": "文章访问数已统计（开发调试模式）"}

#测试
@app.get("/")
def read_root():
    return {"Hello": "ArtiView"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
