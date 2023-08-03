# Arti View

简单实用的使用redis统计文章访问量的 `fastapi` 应用 

1. 复制 app下的 config.sample.json 为 config.json

2. 项目目录下新建 `.env` 文件，修改内容

```
APP_PORT=9800
REDIS_PORT=6380
TZ=Asia/Hong_Kong
```

3. 启动容器
 `docker compose up -d`


如需 nginx反代配置：

``` 
location /arti-view/{
    
    proxy_pass http://127.0.0.1:9800/; #docker 容器中配置的端口地址,注意结尾不要遗忘 / 
    
    
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header REMOTE-HOST $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
    proxy_redirect off;

}
```
