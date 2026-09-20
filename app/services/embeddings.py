
import logging
from sentence_transformers import SentenceTransformer

logger=logging.getLogger(__name__)

# Model name for 384-dimensional dense embeddings
MODEL_NAME="all-MiniLM-L6-v2"

logger.info(f"Loading SentenceTransformer model: {MODEL_NAME}...")

# Singleton instance: Loaded ONCE when the module is imported
model = SentenceTransformer(MODEL_NAME)

logger.info("SentenceTransformer model loaded successfully.")

def encode_text(text:str)->list[float]:
    encoded_text=model.encode(text)
    return encoded_text.tolist()

def encode_query(query:str)->list[float]:
    return encode_text(query)