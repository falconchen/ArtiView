import redis
import json

# 配置 Redis 连接
r = redis.Redis(
    host='redis',
    port=6379,    
    ssl=False
)

# 导出 Redis 数据，包括不同类型的值
def export_redis_data(redis_client, file_name):
    keys = redis_client.scan_iter()
    data = {}

    for key in keys:
        try:
            # 将键转换为字符串
            key_str = key.decode()
            # 判断值的类型
            value_type = redis_client.type(key).decode()

            if value_type == 'string':
                value = redis_client.get(key).decode()  # 获取字符串值
            elif value_type == 'list':
                value = redis_client.lrange(key, 0, -1)  # 获取列表
                value = [v.decode() for v in value]  # 解码为字符串
            elif value_type == 'set':
                value = redis_client.smembers(key)  # 获取集合
                value = [v.decode() for v in value]  # 解码为字符串
            elif value_type == 'zset':
                value = redis_client.zrange(key, 0, -1, withscores=True)  # 获取 ZSet
                value = [(v[0].decode(), v[1]) for v in value]  # 解码并保留分数
            elif value_type == 'hash':
                value = redis_client.hgetall(key)  # 获取哈希
                value = {k.decode(): v.decode() for k, v in value.items()}  # 解码键值对
            else:
                value = None  # 如果是未知类型，设置为 None

            # 存储键值
            data[key_str] = {'type': value_type, 'value': value}
        except Exception as e:
            print(f"跳过无法处理的键: {key}, 错误: {e}")

    # 保存到 JSON 文件
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

export_redis_data(r, 'redis_full_data.json')
print("数据已成功导出到 redis_full_data.json")
