
## 1.0版本已经封库 除了bug 不做新需求开发，master 做2.0版本库  

##  环境

- python3.6

- 依赖
    - 新增依赖
    ```bash
    pip freeze > requirments.txt
    ```
    - 导入依赖
    ```bash
    pip install -r requirments.txt
    ```

- 环境变量


```bash
vim ~/.bashrc
```
```bash
export DXX_DB_HOST='ip地址'
export DXX_DB_NAME='数据库名字'
export DXX_DB_USER='数据库用户名'
export DXX_DB_PWD='数据库密码'

export DXXAPPID='appid'
export DXXAPPSECRET='appsecret'

```

```bash
source ~/.bashrc
```

## 数据库迁移

更改model后使用

- 生成迁移文件

```bash
alembic revision --autogenerate -m 'add'
```

- 执行
```bash
alembic upgrade head
```

- 回滚
```bash
alembic downgrade 上个版本号 # 可在本次迁移文件头部中找到'Revises' 
```

## 启动和关闭
- 启动
```bash
./start.sh start
```

- 重启
```bash
./start.sh restart
```
- 关闭
```bash
./start.sh stop
```
#### 119测试服

- 数据库迁移需要先进入容器，在任意目录下使用 `ddd` 可进入容器bash下

- 容器外任意目录下使用 `dss` 可重启服务

- redis
```bash
redis-server /usr/local/redis/redis.conf
```

- supervisor
```bash
supervisord -c /opt/python_planet/supervisord.conf
```

- nginx && mysql
```bash
nginx && service mysql start
```

## 日志

```bash
/tmp/planet/log*
```
## 错误码
```
405001 参数错误
405002 方法不支持
405003 无权限
405004 not found
405005 系统错误
405006 接口未注册
405007 未登录
405008 重复数据
405009 敬请期待
405010
405011 状态错误
```

