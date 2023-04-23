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
        print("exit")


def _console(cfg: Config) -> bool:
    """Run the console."""

    contents, lang, identify = get_contents()

    print("The article has been retrieved, and the number of text fragments is:", len(contents))
    for content in contents:
        print('\t', content)

    ai = AI(cfg)
    storage = Storage.create_storage(cfg)

    print("=====================================")
    if storage.been_indexed(identify):
        print("The article has already been indexed, so there is no need to index it again.")
        print("=====================================")
    else:
        # 1. 对文章的每个段落生成embedding
        # 1. Generate an embedding for each paragraph of the article.
        embeddings, tokens = ai.create_embeddings(contents)
        print(f"Embeddings have been created with {len(embeddings)} embeddings, using {tokens} tokens, "
              f"costing ${tokens / 1000 * 0.0004}")

        storage.add_all(embeddings, identify)
        print("The embeddings have been saved.")
        print("=====================================")

    while True:
        query = input("Please enter your query (/help to view commands):")
        if query.startswith("/"):
            if query == "/quit":
                return False
            elif query == "/reset":
                return True
            elif query == "/summary":
                # 生成embedding式摘要，根据不同的语言使用有基于SIF的加权平均或一般的直接求平均
                # Generate an embedding-based summary, using weighted average based on SIF or direct average based on the language.
                ai.generate_summary(storage.get_all_embeddings(identify), num_candidates=100,
                                    use_sif=lang not in ['zh', 'ja', 'ko', 'hi', 'ar', 'fa'])
                continue
            elif query == "/reindex":
                # 重新索引，会清空数据库
                # Re-index, which will clear the database.
                storage.clear(identify)
                embeddings, tokens = ai.create_embeddings(contents)
                print(f"Embeddings have been created with {len(embeddings)} embeddings, using {tokens} tokens, "
                      f"costing ${tokens / 1000 * 0.0004}")

                storage.add_all(embeddings, identify)
                print("The embeddings have been saved.")
                print("=====================================")
                continue
            elif query == "/help":
                print("Enter /summary to generate an embedding-based summary.")
                print("Enter /reindex to re-index the article.")
                print("Enter /reset to start over.")
                print("Enter /quit to exit.")
                print("Enter any other content for a query.")
                continue
            else:
                print("Invalid command.")
                print("Enter /summary to generate an embedding-based summary.")
                print("Enter /reindex to re-index the article.")
                print("Enter /reset to start over.")
                print("Enter /quit to exit.")
                print("Enter any other content for a query.")
                continue
        else:
            # 1. 生成关键词
            # 1. Generate keywords.
            print("Generate keywords.")
            keywords = ai.get_keywords(query)
            # 2. 对问题生成embedding
            # 2. Generate an embedding for the question.
            _, embedding = ai.create_embedding(keywords)
            # 3. 从数据库中找到最相似的片段
            # 3. Find the most similar fragments from the database.
            texts = storage.get_texts(embedding, identify)
            print("Related fragments found (first 5):")
            for text in texts[:5]:
                print('\t', text)
            # 4. 把相关片段推给AI，AI会根据这些片段回答问题
            # 4. Push the relevant fragments to the AI, which will answer the question based on these fragments.
            ai.completion(query, texts)
            print("=====================================")
