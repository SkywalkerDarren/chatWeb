# ChatWeb

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/SkywalkerDarren/chatWeb/blob/master/example.ipynb)

ChatWeb可以爬取任意网页或PDF，DOCX，TXT文件并提取正文，可以生成嵌入式概要，可以根据正文内容回答你的问题。
基于gpt3.5的chatAPI和embeddingAPI，以及向量数据库实现。

# 基本原理

基本类似于现有的chatPDF，自动化客服AI等项目的原理。

1. 爬取网页
2. 提取正文
3. 对于每一段落，使用gpt3.5的embeddingAPI生成向量
4. 每一段落的向量和全文向量做计算，生成概要
5. 将向量和文本对应关系存入向量数据库
6. 对于用户输入，生成关键词
7. 对关键词生成向量
8. 使用向量数据库进行最近邻搜索，返回最相似的文本列表
9. 使用gpt3.5的chatAPI，设计prompt，使其基于最相似的文本列表进行回答

新增的使用关键词生成向量相比直接使用问题生成向量，提高了对相关文本的搜索准确度

就是先把大量文本中提取相关内容，再进行回答，最终可以达到类似突破token限制的效果

# 准备开始

- 安装python3

- 下载本仓库`git clone https://github.com/SkywalkerDarren/chatWeb.git`

- 进入目录`cd chatWeb`

- 复制`config.example.json`为`config.json`

- 编辑`config.json`, 设置`open_ai_key`为你的openai的api key

- 安装依赖

```
pip3 install -r requirements.txt
```

- 运行

```
python3 main.py
```

## Stream模式

- 编辑`config.json`, 设置`use_stream`为`true`

## 模式选择

- 编辑`config.json`, 设置`mode`为`console`或`api`可选择启动模式。
- `console`模式下，输入`/help`查看指令
- `api`模式下，可对外提供api服务，在`config.json`中可设置`api_port`和`api_host`

## OpenAI代理设置

- 编辑`config.json`, 添加`open_ai_proxy`为你的代理地址，如：
```
"open_ai_proxy": {
  "http": "socks5://127.0.0.1:1081",
  "https": "socks5://127.0.0.1:1081"
}
```

## 安装postgresql(可选)

- 编辑`config.json`, 设置`use_postgres`为`true`

- 安装postgresql
    - 默认的sql地址: `postgresql://localhost:5432/mydb`或在`config.json`中设置
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

- pip安装依赖`pip3 install psycopg2`


# Example
```txt
Please enter the link to the article or the file path of the PDF/TXT/DOCX document: https://gutenberg.ca/ebooks/hemingwaye-oldmanandthesea/hemingwaye-oldmanandthesea-00-e.html
Please wait for 10 seconds until the webpage finishes loading.
The article has been retrieved, and the number of text fragments is: 663
...
=====================================
Query fragments used tokens: 7219, cost: $0.0028876
Query fragments used tokens: 7250, cost: $0.0029000000000000002
Query fragments used tokens: 7188, cost: $0.0028752
Query fragments used tokens: 7177, cost: $0.0028708
Query fragments used tokens: 2378, cost: $0.0009512000000000001
Embeddings have been created with 663 embeddings, using 31212 tokens, costing $0.0124848
The embeddings have been saved.
=====================================
Please enter your query (/help to view commands):
```

# TODO
- [x] 支持pdf/txt/docx文件
- [x] 支持免数据库纯内存(faiss)
- [x] 支持Stream
- [x] 支持API
- [x] 支持代理
- [x] 添加colab
- [x] 添加语言支持
- [ ] 其他还没想到的
