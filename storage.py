from pgvector.sqlalchemy import Vector

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from abc import ABC, abstractmethod

Base = declarative_base()
SQL_URL = "postgresql://localhost:5432/mydb"


class Storage(ABC):
    """Abstract Storage class."""

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


class MemoryStorage(Storage):
    """MemoryStorage class."""

    def __init__(self):
        """Initialize the storage."""
        self._embeddings = []

    def add(self, text: str, embedding: list[float]):
        """Add a new embedding."""
        self._embeddings.append((text, embedding))

    def add_all(self, embeddings: list[tuple[str, list[float]]]):
        """Add multiple embeddings."""
        self._embeddings.extend(embeddings)

    def get_texts(self, embedding: list[float], limit=100) -> list[str]:
        """Get the text for the provided embedding."""
        return self._cosine_similarity(embedding)[:limit]

    def _cosine_similarity(self, src: list[float]) -> list[str]:
        """Calculate the cosine similarity between the src and all embeddings."""
        from sklearn.metrics.pairwise import cosine_similarity
        embeddings = [emb for text, emb in self._embeddings]
        similarities = sorted(enumerate(cosine_similarity([src], embeddings)[0]), key=lambda x: x[1], reverse=True)
        result = [self._embeddings[index][0] for index, similarity in similarities]
        return result

    def clear(self):
        """Clear the database."""
        self._embeddings = []


class PostgresStorage:
    """PostgresStorage class."""

    def __init__(self):
        """Initialize the storage."""
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
