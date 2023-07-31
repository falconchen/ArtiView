# main.py

from fastapi import FastAPI, HTTPException, Query
import hashlib
import redis

app = FastAPI()

# 连接 Redis 数据库
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

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


# 接口1：统计文章访问数
@app.post("/count_article_views/")
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

# 生成指定字符的 SHA-1 值
def generate_sha1_hash(string: str):
    sha1_hash = hashlib.sha1(string.encode('utf-8')).hexdigest()
    return {"input_string": string, "sha1_hash": sha1_hash}

# 返回指定字符的 SHA-1 值
@app.get("/get_sha1_hash/")
async def get_sha1_hash(string: str = Query(..., description="待计算 SHA-1 值的字符")):
    return generate_sha1_hash(string)

#测试
@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)