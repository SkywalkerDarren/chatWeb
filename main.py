#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import *

import numpy as np
import openai
from newspaper import Article
from pgvector.sqlalchemy import Vector
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
SQL_URL = "postgresql://localhost:5432/mydb"


def run():
    """Run the application."""
    while True:
        try:
            url = input("请输入文章链接：")
            contents = web_crawler(url)
            break
        except Exception as e:
            print("Error:", e)
    print("文章已抓取，片段数量：", len(contents))
    for content in contents:
        print('\t', content)

    embeddings, tokens = create_embeddings(contents)
    print("已创建嵌入，嵌入数量：", len(embeddings), "，使用的令牌数：", tokens, "，花费：", tokens / 1000 * 0.0004, "美元")

    storage = Storage()
    storage.clear()
    storage.add_all(embeddings)
    print("已存储嵌入")
    print("=====================================")

    summary = generate_summary(embeddings, num_candidates=20)
    print(f"已生成摘要：{summary}")
    print("=====================================")

    limit = 30
    while True:

        query = input("请输入查询(help可查看指令)：")
        if query == "quit":
            break
        elif query.startswith("limit"):
            try:
                limit = int(query.split(" ")[1])
                print("已设置limit为", limit)
            except Exception as e:
                print("设置limit失败", e)
            continue
        elif query == "help":
            print("输入limit [数字]设置limit")
            print("输入quit退出")
            continue
        embedding = create_embedding(query)
        texts = storage.get_texts(embedding[1], limit)
        print("已找到相关片段：")
        for text in texts:
            print('\t', text)

        answer = completion(query, texts)
        print(answer.strip())
        print("=====================================")

    storage.clear()


def web_crawler(url) -> list[str]:
    """Run the web crawler."""
    article = Article(url)
    article.download()
    article.parse()
    contents = [text.strip() for text in article.text.splitlines() if text.strip()]
    other = [article.title]
    contents.extend(text.strip() for text in other if text.strip())
    return contents


def completion(query: str, context: list[str]) -> str:
    """Create a completion."""
    lens = [len(text) for text in context]

    maximum = 3000
    for index, l in enumerate(lens):
        maximum -= l
        if maximum < 0:
            context = context[:index + 1]
            print("超过最大长度，截断到前", index + 1, "个片段")
            break

    text = "\n".join(f"{index}. {text}" for index, text in enumerate(context))
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {'role': 'system',
             'content': f'你是一个有帮助的AI文章助手，以下是从文中搜索到具有相关性的文章内容片段，相关性从高到底排序：\n\n{text}'},
            {'role': 'user', 'content': query},
        ],
    )
    print("使用的tokens：", response.usage.total_tokens, "，花费：", response.usage.total_tokens / 1000 * 0.002, "美元")
    return response.choices[0].message.content


def create_embedding(text: str) -> (str, list[float]):
    """Create an embedding for the provided text."""
    embedding = openai.Embedding.create(model="text-embedding-ada-002", input=text)
    return text, embedding.data[0].embedding


def create_embeddings(input: list[str]) -> (list[tuple[str, list[float]]], int):
    """Create embeddings for the provided input."""
    result = []
    # limit about 1000 tokens per request
    lens = [len(text) for text in input]
    query_len = 0
    start_index = 0
    tokens = 0

    def get_embedding(input_slice: list[str]):
        embedding = openai.Embedding.create(model="text-embedding-ada-002", input=input_slice)
        return [(text, data.embedding) for text, data in zip(input_slice, embedding.data)], embedding.usage.total_tokens

    for index, l in enumerate(lens):
        query_len += l
        if query_len > 4096:
            ebd, tk = get_embedding(input[start_index:index + 1])
            query_len = 0
            start_index = index + 1
            tokens += tk
            result.extend(ebd)

    if query_len > 0:
        ebd, tk = get_embedding(input[start_index:])
        tokens += tk
        result.extend(ebd)
    return result, tokens


def generate_summary(embeddings, num_candidates=3):
    paragraphs = [e[0] for e in embeddings]
    embeddings = np.array([e[1] for e in embeddings])
    # 计算每个段落与整个文本的相似度分数
    similarity_scores = cosine_similarity(embeddings, embeddings[0].reshape(1, -1)).flatten()

    # 选择具有最高相似度分数的段落作为摘要的候选段落
    candidate_indices = np.argsort(similarity_scores)[::-1][:num_candidates]
    candidate_paragraphs = [paragraphs[i] for i in candidate_indices]

    print("完成计算，开始生成摘要")

    lens = [len(text) for text in candidate_paragraphs]

    maximum = 3000
    for index, l in enumerate(lens):
        maximum -= l
        if maximum < 0:
            candidate_paragraphs = candidate_paragraphs[:index + 1]
            print("超过最大长度，截断到前", index + 1, "个片段")
            break

    text = "\n".join(f"{index}. {text}" for index, text in enumerate(candidate_paragraphs))
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {'role': 'system',
             'content': f'你是一个有帮助的AI文章助手，以下是从文中搜索到具有相关性的文章内容片段，相关性从高到底排序，你需要从这些相关内容中总结全文内容，最后的结果需要用中文展示：\n\n{text}\n\n中文总结：'},
        ],
    )
    print("使用的tokens：", response.usage.total_tokens, "，花费：", response.usage.total_tokens / 1000 * 0.002, "美元")
    return response.choices[0].message.content


class Storage:
    """Storage class."""

    def __init__(self):
        """Initialize the storage."""
        self._postgresql = SQL_URL
        self._engine = create_engine(self._postgresql)
        Base.metadata.create_all(self._engine)
        Session = sessionmaker(bind=self._engine)
        self._session = Session()

    def add(self, text: str, embedding: list[float]):
        """Add a new embedding."""
        self._session.add(EmbeddingEntity(text=text, embedding=embedding))
        self._session.commit()

    def add_all(self, embeddings: list[tuple[str, list[float]]]):
        """Add multiple embeddings."""
        data = [EmbeddingEntity(text=text, embedding=embedding) for text, embedding in embeddings]
        self._session.add_all(data)
        self._session.commit()

    def get_texts(self, embedding: List[float], limit=30) -> List[str]:
        """Get the text for the provided embedding."""
        result = self._session.query(EmbeddingEntity).order_by(
            EmbeddingEntity.embedding.cosine_distance(embedding)).limit(limit).all()
        return [s.text for s in result]

    def clear(self):
        """Clear the database."""
        self._session.query(EmbeddingEntity).delete()
        self._session.commit()

    def __del__(self):
        """Close the session."""
        self._session.close()


class EmbeddingEntity(Base):
    __tablename__ = 'embedding'
    id = Column(Integer, primary_key=True)
    text = Column(String)
    embedding = Column(Vector(1536))


if __name__ == '__main__':
    run()
