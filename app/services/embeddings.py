import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

EXPECTED_DIM = 384  # must match Vector(384) in models.py


@lru_cache
def get_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s ...", settings.MODEL_NAME)
    model = SentenceTransformer(settings.MODEL_NAME)
    dim = model.get_embedding_dimension()
    if dim != EXPECTED_DIM:
        logger.warning(
            "Model dim=%d but DB column is vector(%d) — inserts will fail!",
            dim, EXPECTED_DIM,
        )
    logger.info("Embedding model ready (dim=%d)", dim)
    return model


def encode_text(text: str) -> list[float]:
    return get_model().encode(text, normalize_embeddings=True).tolist()


def encode_note(title: str, content: str) -> list[float]:
    """Single composition used by BOTH create and update — never inline this f-string elsewhere."""
    return encode_text(f"{title}\n{content}")


def encode_query(query: str) -> list[float]:
    return encode_text(query)