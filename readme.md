# ChatWeb

ChatWeb可以爬取任意网页并提取正文，生成概要，然后根据正文内容回答你的问题。
目前是个原理展示的Demo，还没有细分逻辑。
基于gpt3.5的chatAPI和embeddingAPI，配合向量数据库。

# 基本原理

基本类似于现有的chatPDF，自动化客服AI等项目的原理。

1. 爬取网页
2. 提取正文
3. 对于每一段落，使用gpt3.5的embeddingAPI生成向量
4. 每一段落的向量和全文向量做计算，生成概要
5. 将向量和文本对应关系存入向量数据库
6. 对于用户输入，生成向量
7. 使用向量数据库进行最近邻搜索，返回最相似的文本列表
8. 使用gpt3.5的chatAPI，设计prompt，使其基于最相似的文本列表进行回答

就是先把大量文本中提取相关内容，再进行回答，最终可以达到类似突破token限制的效果

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
