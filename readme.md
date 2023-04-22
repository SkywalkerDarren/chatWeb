# ChatWeb

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/SkywalkerDarren/chatWeb/blob/master/example.ipynb)

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

- 停止对`config.json`的跟踪`git update-index --assume-unchanged config.json`

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
请输入文章链接或pdf/txt/docx文件路径：https://gutenberg.ca/ebooks/clynes-when/clynes-when-00-h.html
文章已抓取，片段数量： 148
...
查询片段 使用的tokens： 7189 ，花费： 0.0028756000000000003 美元
查询片段 使用的tokens： 1438 ，花费： 0.0005752 美元
已创建嵌入，嵌入数量： 148 ，使用的令牌数： 8627 ，花费： 0.0034508000000000004 美元
已存储嵌入
=====================================
完成计算，开始生成摘要
超过最大长度，截断到前 29 个片段
使用的tokens： 3606 ，花费： 0.007212 美元
文章描写了英国社会在作者成长过程中取得的变革和进步。该国政府通过各种立法解决了医疗、失业、工伤等问题，改善了工人和儿童的生活，提供了更多的教育和康乐机会。社会福利制度也在不断发展，注重母婴健康，为孩子们提供更好的成长环境。尽管取得了这些成就，但文章也指出仍有许多问题需要解决，如教育个性化和培养卓越人才等。作者鼓励人们意识到已取得的进步，但也不应忘记还有许多工作要做。
=====================================
请输入查询(help可查看指令)：文章中英国社会取得了哪些进步
已找到相关片段（前5个）：
	 Relate that significant change to other remarkable changes and it is possible to have some idea of what this new and developing social England means to all of us. And to the weaving of this fabric of our material life our magnificent social services have made a great contribution.
	 And now what does our country do for its citizens when they are grown-up and go out in the world? It is impossible to answer that question without feeling a glow of pride in our achievements. Looking back again on the changes I have seen in my own lifetime, I am amazed at the tremendous strides that have been made in providing greater comfort, happiness and security for the men and women of Britain. I am not complacent; I am not satisfied. There are many reforms yet to be made; much progress still to be registered, but it would be ungenerous and unreal not to recognise all that has been done.
	 I would like to quote again from this valuable and revealing book a passage which seems to me singularly appropriate at the moment: "Nothing is more exasperating to those to whom social reform is religion in action than the readiness with which the English neglect, forget or minimise their achievements. The visitor from Central Europe will tell with enthusiasm of the decline of illiteracy in his country since the war. The Englishman scarcely knows the meaning of the word, still less does he trouble to enquire whether illiteracy still exists in England.
	 There is more opportunity for leisure; in the old days all work and no play made Jack a very dull boy. Hours of labour are shorter, conditions of employment better, wages higher. And much of this improved standard is due to the work of the Trade Union and Labour Movement which has banded men and women together in democratic organisations in order to make life more tolerable for all. But, of course, it is not the work of the Trade Union and Labour Movement only. To pioneers like Robert Owen and Lord Shaftesbury, to countless men and women of goodwill who have never identified themselves with any Party, to progressively minded people in all the political Parties, the workers and the nation owe an incalculable debt.
	 All this is what Britain has done, and is doing, for its women and children with the object of building up a healthy people fit to play their proper part in the work of the nation.
使用的tokens： 1022 ，花费： 0.0020440000000000002 美元
文章提到英国在多个方面取得了进步，包括提供更好的福利、增加休闲时间、改善劳动条件、提高工资、改进教育系统、改善妇女和儿童的状况、减少未成年犯罪、创建公共机构等等。这些进步为英国的发展和社会进步做出了巨大贡献。
=====================================
请输入查询(help可查看指令)：
```

# TODO
- [x] 支持pdf/txt/docx文件
- [x] 支持免数据库纯内存(faiss)
- [x] 支持Stream
- [x] 支持API
- [x] 支持代理
- [x] 添加colab
- [ ] 其他还没想到的
