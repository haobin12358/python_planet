
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
## 启动和关闭
-启动
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

