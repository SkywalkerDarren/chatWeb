import os.path
import faiss
import numpy as np
import pandas as pd
from pgvector.sqlalchemy import Vector

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from abc import ABC, abstractmethod

Base = declarative_base()


class Storage(ABC):
    """Abstract Storage class."""

    # factory method
    @staticmethod
    def create_storage(storage_type: str) -> 'Storage':
        """Create a storage object."""
        if storage_type == 'index':
            return _IndexStorage()
        elif storage_type == 'postgres':
            return _PostgresStorage()
        else:
            raise ValueError(f'Unknown storage type: {storage_type}')

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
    def clear(self):
        """Clear the database."""
        pass


class _IndexStorage(Storage):
    """IndexStorage class."""

    def __init__(self):
        """Initialize the storage."""
        self.texts = None
        self.index = None
        self._load()

    def add(self, text: str, embedding: list[float]):
        """Add a new embedding."""
        array = np.array([embedding])
        self.texts = pd.concat([self.texts, pd.DataFrame({'index': len(self.texts), 'text': text}, index=[0])])
        self.index.add(array)
        self._save()

    def add_all(self, embeddings: list[tuple[str, list[float]]]):
        """Add multiple embeddings."""
        self.texts = pd.concat([self.texts, pd.DataFrame(
            {'index': len(self.texts) + i, 'text': text} for i, (text, _) in enumerate(embeddings))])
        array = np.array([emb for text, emb in embeddings])
        self.index.add(array)
        self._save()

    def get_texts(self, embedding: list[float], limit=10) -> list[str]:
        _, indexs = self.index.search(np.array([embedding]), limit)
        return self.texts.iloc[indexs[0]].text.tolist()

    def clear(self):
        """Clear the database."""
        self._delete()

    def _save(self):
        self.texts.to_csv('texts.csv')
        faiss.write_index(self.index, 'index.bin')

    def _load(self):
        if os.path.exists('texts.csv') and os.path.exists('index.bin'):
            self.texts = pd.read_csv('texts.csv')
            self.index = faiss.read_index('index.bin')
        else:
            self.texts = pd.DataFrame(columns=['index', 'text'])
            self.index = faiss.IndexFlatIP(1536)

    def _delete(self):
        try:
            os.remove('texts.csv')
            os.remove('index.bin')
        except FileNotFoundError:
            pass
        self._load()


class _PostgresStorage(Storage):
    """PostgresStorage class."""

    def __init__(self):
        """Initialize the storage."""
        from main import SQL_URL
        self._postgresql = SQL_URL
        self._engine = create_engine(self._postgresql)
        Base.metadata.create_all(self._engine)
        session = sessionmaker(bind=self._engine)
        self._session = session()

    def add(self, text: str, embedding: list[float]):
        """Add a new embedding."""
        self._session.add(EmbeddingEntity(text=text, embedding=embedding))
        self._session.commit()

    def add_all(self, embeddings: list[tuple[str, list[float]]]):
        """Add multiple embeddings."""
        data = [EmbeddingEntity(text=text, embedding=embedding) for text, embedding in embeddings]
        self._session.add_all(data)
        self._session.commit()

    def get_texts(self, embedding: list[float], limit=100) -> list[str]:
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
