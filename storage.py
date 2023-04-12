import os.path
from typing import Optional

import faiss
import numpy as np
import pandas as pd
from pgvector.sqlalchemy import Vector

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from abc import ABC, abstractmethod

from config import Config

Base = declarative_base()


class Storage(ABC):
    """Abstract Storage class."""

    # factory method
    @staticmethod
    def create_storage(cfg: Config) -> 'Storage':
        """Create a storage object."""
        if cfg.use_postgres:
            return _PostgresStorage(cfg)
        else:
            return _IndexStorage(cfg)

    @abstractmethod
    def add_all(self, embeddings: list[tuple[str, list[float]]], name: str):
        """Add multiple embeddings."""
        pass

    @abstractmethod
    def get_texts(self, embedding: list[float], name: str, limit=100) -> list[str]:
        """Get the text for the provided embedding."""
        pass

    @abstractmethod
    def get_all_embeddings(self, name: str):
        """Get all embeddings."""
        pass

    @abstractmethod
    def clear(self, name: str):
        """Clear the database."""
        pass

    @abstractmethod
    def been_indexed(self, name: str) -> bool:
        """Check if the database has been indexed."""
        pass


class _IndexStorage(Storage):
    """IndexStorage class."""

    def __init__(self, cfg: Config):
        """Initialize the storage."""
        self._cfg = cfg

    def add_all(self, embeddings: list[tuple[str, list[float]]], name):
        """Add multiple embeddings."""
        texts, index = self._load(name)
        ids = np.array([len(texts) + i for i, _ in enumerate(embeddings)])
        texts = pd.concat([texts, pd.DataFrame(
            {'index': len(texts) + i, 'text': text} for i, (text, _) in enumerate(embeddings))])
        array = np.array([emb for text, emb in embeddings])
        index.add_with_ids(array, ids)
        self._save(texts, index, name)

    def get_texts(self, embedding: list[float], name: str, limit=10) -> list[str]:
        """Get the text for the provided embedding."""
        texts, index = self._load(name)
        _, indexs = index.search(np.array([embedding]), limit)
        return [f'paragraph {p}: {t}' for _, p, t in texts.iloc[indexs[0]].values]

    def get_all_embeddings(self, name: str):
        texts, index = self._load(name)
        texts = texts.text.tolist()
        embeddings = index.reconstruct_n(0, len(texts))
        return list(zip(texts, embeddings))

    def clear(self, name: str):
        """Clear the database."""
        self._delete(name)

    def been_indexed(self, name: str) -> bool:
        return os.path.exists(os.path.join(self._cfg.index_path, f'{name}.csv')) and os.path.exists(
            os.path.join(self._cfg.index_path, f'{name}.bin'))

    def _save(self, texts, index, name: str):
        texts.to_csv(os.path.join(self._cfg.index_path, f'{name}.csv'))
        faiss.write_index(index, os.path.join(self._cfg.index_path, f'{name}.bin'))

    def _load(self, name: str):
        if self.been_indexed(name):
            texts = pd.read_csv(os.path.join(self._cfg.index_path, f'{name}.csv'))
            index = faiss.read_index(os.path.join(self._cfg.index_path, f'{name}.bin'))
        else:
            texts = pd.DataFrame(columns=['index', 'text'])
            # IDMap2 with Flat
            index = faiss.index_factory(1536, "IDMap2,Flat", faiss.METRIC_INNER_PRODUCT)
        return texts, index

    def _delete(self, name: str):
        try:
            os.remove(os.path.join(self._cfg.index_path, f'{name}.csv'))
            os.remove(os.path.join(self._cfg.index_path, f'{name}.bin'))
        except FileNotFoundError:
            pass


def singleton(cls):
    instances = {}

    def get_instance(cfg):
        if cls not in instances:
            instances[cls] = cls(cfg)
        return instances[cls]

    return get_instance


@singleton
class _PostgresStorage(Storage):
    """PostgresStorage class."""

    def __init__(self, cfg: Config):
        """Initialize the storage."""
        self._postgresql = cfg.postgres_url
        self._engine = create_engine(self._postgresql)
        Base.metadata.create_all(self._engine)
        session = sessionmaker(bind=self._engine)
        self._session = session()

    def add_all(self, embeddings: list[tuple[str, list[float]]], name: str):
        """Add multiple embeddings."""
        data = [self.EmbeddingEntity(text=text, embedding=embedding, name=name) for text, embedding in embeddings]
        self._session.add_all(data)
        self._session.commit()

    def get_texts(self, embedding: list[float], name: str, limit=100) -> list[str]:
        """Get the text for the provided embedding."""
        result = self._session.query(self.EmbeddingEntity).where(self.EmbeddingEntity.name == name).order_by(
            self.EmbeddingEntity.embedding.cosine_distance(embedding)).limit(limit).all()
        return [f'paragraph {s.id}: {s.text}' for s in result]

    def get_all_embeddings(self, name: str):
        """Get all embeddings."""
        result = self._session.query(self.EmbeddingEntity).where(self.EmbeddingEntity.name == name).all()
        return [(s.text, s.embedding) for s in result]

    def clear(self, name: str):
        """Clear the database."""
        self._session.query(self.EmbeddingEntity).where(self.EmbeddingEntity.name == name).delete()
        self._session.commit()

    def been_indexed(self, name: str) -> bool:
        return self._session.query(self.EmbeddingEntity).filter_by(name=name).first() is not None

    def __del__(self):
        """Close the session."""
        self._session.close()

    class EmbeddingEntity(Base):
        __tablename__ = 'embedding'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        text = Column(String)
        embedding = Column(Vector(1536))
