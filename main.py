#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ai import AI
from config import Config
from storage import Storage


def console(cfg: Config):
    """Run the console."""
    from contents import get_contents

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
            break
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


def api(cfg: Config):
    """Run the API."""
    import uvicorn
    from fastapi import FastAPI, UploadFile, File
    import shutil
    import os
    import xxhash
    from pydantic import BaseModel
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.exceptions import HTTPException
    from fastapi.exceptions import RequestValidationError
    from contents import web_crawler_newspaper, extract_text_from_txt, extract_text_from_docx, \
        extract_text_from_pdf

    cfg.use_stream = False
    ai = AI(cfg)

    app = FastAPI()

    class CrawlerUrlRequest(BaseModel):
        url: str

    @app.post("/crawler_url")
    async def crawler_url(req: CrawlerUrlRequest):
        """Crawler the URL."""
        contents, lang = web_crawler_newspaper(req.url)
        hash_id = xxhash.xxh3_128_hexdigest('\n'.join(contents))
        tokens = _save_to_storage(contents, hash_id)
        return {"code": 0, "msg": "ok", "data": {"uri": f"{hash_id}/{lang}", "tokens": tokens}}

    def _save_to_storage(contents, hash_id):
        storage = Storage.create_storage(cfg)
        if storage.been_indexed(hash_id):
            return 0
        else:
            embeddings, tokens = ai.create_embeddings(contents)
            storage.add_all(embeddings, hash_id)
            return tokens

    @app.post("/upload_file")
    async def create_upload_file(file: UploadFile = File(...)):
        """Upload file."""
        # save file to disk
        file_name = file.filename
        os.makedirs('./upload', exist_ok=True)
        upload_path = os.path.join('./upload', file_name)
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if file_name.endswith('.pdf'):
            contents, lang = extract_text_from_pdf(upload_path)
        elif file_name.endswith('.txt'):
            contents, lang = extract_text_from_txt(upload_path)
        elif file_name.endswith('.docx'):
            contents, lang = extract_text_from_docx(upload_path)
        else:
            return {"code": 1, "msg": "not support", "data": {}}
        hash_id = xxhash.xxh3_128_hexdigest('\n'.join(contents))
        tokens = _save_to_storage(contents, hash_id)
        os.remove(upload_path)
        return {"code": 0, "msg": "ok", "data": {"uri": f"{hash_id}/{lang}", "tokens": tokens}}

    @app.get("/summary")
    async def summary(uri: str):
        """Generate summary."""
        hash_id, lang = uri.split('/')
        storage = Storage.create_storage(cfg)
        if not storage or not lang:
            return {"code": 1, "msg": "not found", "data": {}}
        s = ai.generate_summary(storage.get_all_embeddings(hash_id), num_candidates=100,
                                use_sif=lang not in ['zh', 'ja', 'ko', 'hi', 'ar', 'fa'])
        return {"code": 0, "msg": "ok", "data": {"summary": s}}

    class AnswerRequest(BaseModel):
        uri: str
        query: str

    @app.get("/answer")
    async def answer(req: AnswerRequest):
        """Query."""
        hash_id, lang = req.uri.split('/')
        storage = Storage.create_storage(cfg)
        if not storage or not lang:
            return {"code": 1, "msg": "not found", "data": {}}
        _, embedding = ai.create_embedding(req.query)
        texts = storage.get_texts(embedding, hash_id)
        s = ai.completion(req.query, texts)
        return {"code": 0, "msg": "ok", "data": {"answer": s}}

    @app.exception_handler(RequestValidationError)
    async def validate_error_handler(request: Request, exc: RequestValidationError):
        """Error handler."""
        print("validate_error_handler: ", request.url, exc)
        return JSONResponse(
            status_code=400,
            content={"code": 1, "msg": str(exc.errors()), "data": {}},
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc):
        """Error handler."""
        print("http error_handler: ", request.url, exc)
        return JSONResponse(
            status_code=400,
            content={"code": 1, "msg": exc.detail, "data": {}},
        )

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
