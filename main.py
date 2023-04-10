#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import xxhash
from pydantic import BaseModel

from ai import AI
from config import Config
from contents import get_contents, web_crawler_newspaper
from storage import Storage


def console(cfg: Config):
    """Run the console."""
    contents, lang, identify = get_contents()

    print("文章已抓取，片段数量：", len(contents))
    for content in contents:
        print('\t', content)

    ai = AI(cfg)
    storage = Storage.create_storage(cfg, identify)

    print("=====================================")
    if storage.been_indexed():
        print("已经索引过了，不用再索引了")
        print("=====================================")
    else:
        # 1. 对文章的每个段落生成embedding
        embeddings, tokens = ai.create_embeddings(contents)
        print("已创建嵌入，嵌入数量：", len(embeddings), "，使用的令牌数：", tokens, "，花费：", tokens / 1000 * 0.0004,
              "美元")

        storage.add_all(embeddings)
        print("已存储嵌入")
        print("=====================================")

    while True:
        query = input("请输入查询(help可查看指令)：")
        if query == "/quit":
            break
        elif query == "/summary":
            # 生成embedding式摘要，有基于SIF的加权平均和一般的直接求平均，懒得中文分词了这里使用的是直接求平均，英文可以改成SIF
            ai.generate_summary(storage.get_all_embeddings(), num_candidates=100,
                                use_sif=lang not in ['zh', 'ja', 'ko', 'hi', 'ar', 'fa'])
            continue
        elif query == "/reindex":
            # 重新索引，会清空数据库
            storage.clear()
            embeddings, tokens = ai.create_embeddings(contents)
            print("已创建嵌入，嵌入数量：", len(embeddings), "，使用的令牌数：", tokens, "，花费：", tokens / 1000 * 0.0004,
                  "美元")
            storage.add_all(embeddings)
            print("已存储嵌入")
            print("=====================================")
            continue
        elif query == "help":
            print("输入/summary生成嵌入式摘要")
            print("输入/reindex重新索引")
            print("输入/quit退出")
            print("输入其他内容进行查询")
            continue
        else:
            # 1. 对问题生成embedding
            _, embedding = ai.create_embedding(query)
            # 2. 从数据库中找到最相似的片段
            texts = storage.get_texts(embedding)
            print("已找到相关片段（前5个）：")
            for text in texts[:5]:
                print('\t', text)
            # 3. 把相关片段推给AI，AI会根据这些片段回答问题
            ai.completion(query, texts)
            print("=====================================")


def api(cfg: Config):
    """Run the API."""
    import uvicorn
    from fastapi import FastAPI

    cfg.use_stream = False
    ai = AI(cfg)
    storage_dict = {}
    if not cfg.use_postgres:
        for _, _, files in os.walk(cfg.index_path):
            for file in files:
                if file.endswith('.bin') and f'{file[:-4]}.csv' in files:
                    hash_id = file[:-4]
                    storage_dict[hash_id] = Storage.create_storage(cfg, hash_id)

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"code": 0, "msg": "ok", "data": {}}

    class CrawlerUrlRequest(BaseModel):
        url: str

    @app.post("/crawler_url")
    async def crawler_url(req: CrawlerUrlRequest):
        """Crawler the URL."""
        contents, lang = web_crawler_newspaper(req.url)
        hash_id = xxhash.xxh3_128_hexdigest('\n'.join(contents))
        if hash_id not in storage_dict:
            storage = Storage.create_storage(cfg, hash_id)
            if storage.been_indexed():
                tokens = 0
            else:
                embeddings, tokens = ai.create_embeddings(contents)
                storage.add_all(embeddings)
            storage_dict[hash_id] = storage
        else:
            tokens = 0
        return {"code": 0, "msg": "ok", "data": {"uri": f"{hash_id}/{lang}", "tokens": tokens}}

    @app.get("/summary")
    async def summary(uri: str):
        """Generate summary."""
        hash_id, lang = uri.split('/')
        storage = storage_dict.get(hash_id)
        if not storage or not lang:
            return {"code": 1, "msg": "not found", "data": {}}
        s = ai.generate_summary(storage.get_all_embeddings(), num_candidates=100,
                                use_sif=lang not in ['zh', 'ja', 'ko', 'hi', 'ar', 'fa'])
        return {"code": 0, "msg": "ok", "data": {"summary": s}}

    class AnswerRequest(BaseModel):
        uri: str
        query: str

    @app.get("/answer")
    async def answer(req: AnswerRequest):
        """Query."""
        hash_id, lang = req.uri.split('/')
        storage = storage_dict.get(hash_id)
        if not storage or not lang:
            return {"code": 1, "msg": "not found", "data": {}}
        _, embedding = ai.create_embedding(req.query)
        texts = storage.get_texts(embedding)
        s = ai.completion(req.query, texts)
        return {"code": 0, "msg": "ok", "data": {"answer": s}}

    # run the API
    uvicorn.run(app, host=cfg.api_host, port=cfg.api_port)


def run():
    """Run the program."""
    cfg = Config()

    mode = cfg.mode
    if mode == 'console':
        try:
            console(cfg)
        except KeyboardInterrupt:
            print("退出")
    elif mode == 'api':
        api(cfg)


if __name__ == '__main__':
    run()
