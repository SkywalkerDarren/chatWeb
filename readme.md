# ChatWeb

ChatWeb可以爬取任意网页并提取正文，然后根据正文内容回答你的问题。
目前是个原理展示的Demo，还没有细分逻辑。

# 准备开始

- 安装python3
- 安装postgresql
    - 默认的sql地址: `postgresql://localhost:5432/mydb`
- 安装pgvector插件

编译并安装扩展（支持Postgres 11+）

```bash
git clone --branch v0.4.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install # may need sudo
```

然后在您要使用它的数据库中加载它

```postgresql
CREATE EXTENSION vector;
```

- 环境变量

设置`OPENAI_API_KEY`为你的openai的api key

```shell
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

- 安装依赖

```
pip install -r requirements.txt
```

- 运行

```
python main.py
```
