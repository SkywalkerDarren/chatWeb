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

- 配置环境变量

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

## Stream模式
在main.py中设置`USE_STREAM`为`True`

## 安装postgresql(可选)
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

在main.py中设置`USE_POSTGRES`为`True`


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
使用的tokens： 3699 ，花费： 0.007398 美元
已生成摘要：文章描述了英国社会在近一个世纪内所做出的巨大改变，特别是对妇女和儿童的福利保障。英国已经制定了许多法律法规，以确保每个人都获得公平的教育机会、医疗保障和福利待遇。与50年前相比，英国的教育、医疗、福利和劳动力法规得到了重大改进。英国政府为需要帮助的妇女和儿童提供免费或廉价食品和衣物。此外，英国的贫民窟和缺乏地区得到了重建和扩建。英国还开办了幼儿园和孕产医院，致力于保障孩子们健康、快乐成长。然而，作者指出还有很多需要改进的地方，不管是在教育、医疗、福利还是劳动力领域，英国都有继续前进的道路。
=====================================
请输入查询(help可查看指令)：讲讲还需要改进的地方
已找到相关片段（前5个）：
	 I could go on to tell how under successive Governments—of all parties—the housing conditions of the people have steadily improved. There are still slums, but they become fewer. There is still overcrowding, but it is decreasing.
	 Our educational development has reached a high mark, although there is admittedly much to be done. There is still more to be done in the matters of free feeding and general nutrition. Tremendous strides have been made in curative work. We need faster and greater strides in preventive work. Much has been done there during the last quarter of a century, but much remains.
	 To these improvements I gladly bear testimony. Compared with when I was a boy the condition of the young people is immeasurably better. They are better-fed, better-clothed, better-educated. When I was young, the whole of working-class life was drab, dull and depressing: to-day there is colour and variety that many of we older men never knew.
	 Here is another and a very vital problem—that of nutrition. It is not much good trying to teach an ill-nourished child. The maternity and child welfare legislation gives power to local authorities to provide food free or at cheap rates to necessitous mothers and young children. That this power is not used nearly to the extent that it should be is not the fault of our system, but is due to many local authorities lagging behind. I said in a recent article that by peaceful means we have secured reforms in working-class life beyond the dreams of our fathers. I added: "Much yet remains to be done and by means of a wholesome discontent more will be obtained."
	 His conclusion is as follows: "In the creation of an educated democracy complacent satisfaction with the degree of progress so far achieved can find no place. The millennium is still a long way off. So long as there is one child who has failed to obtain the precise educational treatment his individuality requires; so long as a single child goes hungry, has nowhere to play, fails to receive the medical attention he needs; so long as the nation fails to train and provide scope for every atom of outstanding ability it can find; so long as there are administrators or teachers who feel no sense of mission, who cannot administer or who cannot teach, the system will remain incomplete.
超过最大长度，截断到前 52 个片段
使用的tokens： 3669 ，花费： 0.007338 美元
在这篇文章中，虽然作者提到了许多社会改革的进步和成就，但他也承认仍有需要改进的地方，比如儿童营养、工人的福利、教育制度以及公共服务的利用率等等。而且，他强调了持续的改进和不断的努力是必要的，以实现更公正和更平等的社会。

然而，这篇文章是在1941年写的，现在已经过去了80多年。虽然很多问题得到了改善，但还有许多仍然存在。例如，许多人仍然面临着低收入、低福利和高房价的问题，许多儿童仍然面临营养不良和教育资源不足的问题，还有许多社区缺乏充足的医疗和公共服务。因此，我们需要继续努力，追求更好的生活和更公正的社会。
=====================================
请输入查询(help可查看指令)：
```

# TODO
- [x] 支持pdf/txt/docx文件
- [x] 支持免数据库纯内存(faiss)
- [x] 支持Stream
- [ ] 其他还没想到的
