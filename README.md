# Arti View

简单实用的使用redis统计文章访问量的 `fastapi` 应用 

nginx反代配置
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
