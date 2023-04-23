import os
import shutil

import uvicorn
import xxhash
from fastapi import FastAPI, UploadFile, File
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from ai import AI
from config import Config
from contents import web_crawler_newspaper, extract_text_from_txt, extract_text_from_docx, \
    extract_text_from_pdf
from storage import Storage


def api(cfg: Config):
    """Run the API."""

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
        keywords = ai.get_keywords(req.query)
        _, embedding = ai.create_embedding(keywords)
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
