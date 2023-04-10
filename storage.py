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
    def create_storage(cfg: Config, name: str) -> 'Storage':
        """Create a storage object."""
        if cfg.use_postgres:
            return _PostgresStorage(cfg, name)
        else:
            return _IndexStorage(cfg, name)

    @abstractmethod
    def add(self, text: str, embedding: list[float]):
        """Add a new embedding."""
        pass

    @abstractmethod
    def add_all(self, embeddings: list[tuple[str, list[float]]]):
        """Add multiple embeddings."""
        pass

    @abstractmethod
    def get_texts(self, embedding: list[float], limit=100) -> list[str]:
        """Get the text for the provided embedding."""
        pass

    @abstractmethod
    def get_all_embeddings(self):
        """Get all embeddings."""
        pass

    @abstractmethod
    def clear(self):
        """Clear the database."""
        pass

    @abstractmethod
    def been_indexed(self) -> bool:
        """Check if the database has been indexed."""
        pass


class _IndexStorage(Storage):
    """IndexStorage class."""

    def __init__(self, cfg: Config, name: str):
        """Initialize the storage."""
        self.texts = None
        self.index: Optional[faiss.IndexIDMap] = None
        self._cfg = cfg
        self._name = name
        self._load()

    def add(self, text: str, embedding: list[float]):
        """Add a new embedding."""
        array = np.array([embedding])
        self.texts = pd.concat([self.texts, pd.DataFrame({'index': len(self.texts), 'text': text}, index=[0])])
        self.index.add_with_ids(array, np.array([len(self.texts) - 1]))
        self._save()

    def add_all(self, embeddings: list[tuple[str, list[float]]]):
        """Add multiple embeddings."""
        ids = np.array([len(self.texts) + i for i, _ in enumerate(embeddings)])
        self.texts = pd.concat([self.texts, pd.DataFrame(
            {'index': len(self.texts) + i, 'text': text} for i, (text, _) in enumerate(embeddings))])
        array = np.array([emb for text, emb in embeddings])
        self.index.add_with_ids(array, ids)
        self._save()

    def update_embedding(self, index: int, embedding: list[float]):
        """Update the embedding for the provided index."""
        self.index.remove_ids(np.array([index]))
        self.index.add_with_ids(np.array([embedding]), np.array([index]))
        self._save()

    def get_texts(self, embedding: list[float], limit=10) -> list[str]:
        _, indexs = self.index.search(np.array([embedding]), limit)
        return self.texts.iloc[indexs[0]].text.tolist()

    def get_all_embeddings(self):
        texts = self.texts.text.tolist()
        embeddings = self.index.reconstruct_n(0, len(self.texts))
        return list(zip(texts, embeddings))

    def clear(self):
        """Clear the database."""
        self._delete()

    def been_indexed(self) -> bool:
        return os.path.exists(os.path.join(self._cfg.index_path, f'{self._name}.csv')) and os.path.exists(
            os.path.join(self._cfg.index_path, f'{self._name}.bin'))

    def _save(self):
        self.texts.to_csv(os.path.join(self._cfg.index_path, f'{self._name}.csv'))
        faiss.write_index(self.index, os.path.join(self._cfg.index_path, f'{self._name}.bin'))

    def _load(self):
        if self.been_indexed():
            self.texts = pd.read_csv(os.path.join(self._cfg.index_path, f'{self._name}.csv'))
            self.index = faiss.read_index(os.path.join(self._cfg.index_path, f'{self._name}.bin'))
        else:
            self.texts = pd.DataFrame(columns=['index', 'text'])
            # IDMap2 with Flat
            self.index = faiss.index_factory(1536, "IDMap2,Flat", faiss.METRIC_INNER_PRODUCT)

    def _delete(self):
        try:
            os.remove(f'{self._name}.csv')
            os.remove(f'{self._name}.bin')
        except FileNotFoundError:
            pass
        self._load()


class _PostgresStorage(Storage):
    """PostgresStorage class."""

    def __init__(self, cfg: Config, name: str):
        """Initialize the storage."""
        self._postgresql = cfg.postgres_url
        self._engine = create_engine(self._postgresql)
        Base.metadata.create_all(self._engine)
        session = sessionmaker(bind=self._engine)
        self._session = session()
        self._name = name

    def add(self, text: str, embedding: list[float]):
        """Add a new embedding."""
        self._session.add(self.EmbeddingEntity(text=text, embedding=embedding, name=self._name))
        self._session.commit()

    def add_all(self, embeddings: list[tuple[str, list[float]]]):
        """Add multiple embeddings."""
        data = [self.EmbeddingEntity(text=text, embedding=embedding, name=self._name) for text, embedding in embeddings]
        self._session.add_all(data)
        self._session.commit()

    def get_texts(self, embedding: list[float], limit=100) -> list[str]:
        """Get the text for the provided embedding."""
        result = self._session.query(self.EmbeddingEntity).order_by(
            self.EmbeddingEntity.embedding.cosine_distance(embedding)).limit(limit).all()
        return [s.text for s in result]

    def get_all_embeddings(self):
        """Get all embeddings."""
        result = self._session.query(self.EmbeddingEntity).where(self.EmbeddingEntity.name == self._name).all()
        return [(s.text, s.embedding) for s in result]

    def clear(self):
        """Clear the database."""
        self._session.query(self.EmbeddingEntity).delete()
        self._session.commit()

    def been_indexed(self) -> bool:
        return self._session.query(self.EmbeddingEntity).filter_by(name=self._name).first() is not None

    def __del__(self):
        """Close the session."""
        self._session.close()

    class EmbeddingEntity(Base):
        __tablename__ = 'embedding'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        text = Column(String)
        embedding = Column(Vector(1536))
