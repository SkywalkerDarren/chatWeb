from ai import AI
from config import Config
from storage import Storage
from contents import get_contents


def console(cfg: Config):
    try:
        while True:
            if not _console(cfg):
                return
    except KeyboardInterrupt:
        print("退出")


def _console(cfg: Config) -> bool:
    """Run the console."""

    contents, lang, identify = get_contents()

    print("文章已抓取，片段数量：", len(contents))
    for content in contents:
        print('\t', content)

    ai = AI(cfg)
    storage = Storage.create_storage(cfg)

    print("=====================================")
    if storage.been_indexed(identify):
        print("已经索引过了，不用再索引了")
        print("=====================================")
    else:
        # 1. 对文章的每个段落生成embedding
        embeddings, tokens = ai.create_embeddings(contents)
        print("已创建嵌入，嵌入数量：", len(embeddings), "，使用的令牌数：", tokens, "，花费：", tokens / 1000 * 0.0004,
              "美元")

        storage.add_all(embeddings, identify)
        print("已存储嵌入")
        print("=====================================")

    while True:
        query = input("请输入查询(/help可查看指令)：")
        if query == "/quit":
            return False
        elif query == "/reset":
            return True
        elif query == "/summary":
            # 生成embedding式摘要，有基于SIF的加权平均和一般的直接求平均，懒得中文分词了这里使用的是直接求平均，英文可以改成SIF
            ai.generate_summary(storage.get_all_embeddings(identify), num_candidates=100,
                                use_sif=lang not in ['zh', 'ja', 'ko', 'hi', 'ar', 'fa'])
            continue
        elif query == "/reindex":
            # 重新索引，会清空数据库
            storage.clear(identify)
            embeddings, tokens = ai.create_embeddings(contents)
            print("已创建嵌入，嵌入数量：", len(embeddings), "，使用的令牌数：", tokens, "，花费：", tokens / 1000 * 0.0004,
                  "美元")
            storage.add_all(embeddings, identify)
            print("已存储嵌入")
            print("=====================================")
            continue
        elif query == "/help":
            print("输入/summary生成嵌入式摘要")
            print("输入/reindex重新索引")
            print("输入/reset重新开始")
            print("输入/quit退出")
            print("输入其他内容进行查询")
            continue
        else:
            # 1. 对问题生成embedding
            _, embedding = ai.create_embedding(query)
            # 2. 从数据库中找到最相似的片段
            texts = storage.get_texts(embedding, identify)
            print("已找到相关片段（前5个）：")
            for text in texts[:5]:
                print('\t', text)
            # 3. 把相关片段推给AI，AI会根据这些片段回答问题
            ai.completion(query, texts)
            print("=====================================")
