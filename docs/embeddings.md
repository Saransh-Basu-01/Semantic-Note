# Embedding Service Explanation

This file explains how the embedding service loads a model, converts text into
vectors, and keeps FastAPI responsive while embedding text.

## Complete code

```python
import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer
from fastapi.concurrency import run_in_threadpool

from app.config import settings


logger = logging.getLogger(__name__)

EXPECTED_DIM = 384


@lru_cache
def get_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s ...", settings.MODEL_NAME)

    model = SentenceTransformer(settings.MODEL_NAME)

    dim = model.get_embedding_dimension()

    if dim != EXPECTED_DIM:
        logger.warning(
            "Model dim=%d but DB column is vector(%d) — inserts will fail!",
            dim,
            EXPECTED_DIM,
        )

    logger.info("Embedding model ready (dim=%d)", dim)

    return model


# Synchronous core functions

def encode_text(text: str) -> list[float]:
    return get_model().encode(
        text,
        normalize_embeddings=True,
    ).tolist()


def encode_note(title: str, content: str) -> list[float]:
    """
    The same title/content composition is used for note creation and updates.
    """
    return encode_text(f"{title}\n{content}")


def encode_query(query: str) -> list[float]:
    return encode_text(query)


# Async wrappers for FastAPI

async def aencode_note(title: str, content: str) -> list[float]:
    """
    Runs note encoding in a background thread.
    """
    return await run_in_threadpool(
        encode_note,
        title,
        content,
    )


async def aencode_query(query: str) -> list[float]:
    """
    Runs query encoding in a background thread.
    """
    return await run_in_threadpool(
        encode_query,
        query,
    )
```

---

## What is an embedding?

An embedding is a list of numbers that represents the meaning of text.

For example:

```text
"FastAPI supports asynchronous programming."
```

may become a vector like:

```python
[
    0.12,
    -0.04,
    0.31,
    ...
]
```

The actual model produces `384` numbers when using a 384-dimensional model.

These vectors are used for semantic search. Texts with similar meanings should
have vectors that are close to each other.

---

## `EXPECTED_DIM`

```python
EXPECTED_DIM = 384
```

This is the expected number of values in every embedding vector.

It must match the database vector column:

```python
Vector(384)
```

If the model produces 384 values but the database expects 768 values, storing the
embedding will fail.

---

## The `get_model()` function

```python
@lru_cache
def get_model() -> SentenceTransformer:
```

This function loads and returns the sentence-transformer model.

```python
model = SentenceTransformer(settings.MODEL_NAME)
```

The model name comes from the application settings, for example:

```env
MODEL_NAME=all-MiniLM-L6-v2
```

The model dimension is then checked:

```python
dim = model.get_embedding_dimension()
```

If the dimension does not match `EXPECTED_DIM`, a warning is logged.

---

## What is `lru_cache`?

`lru_cache` stores the result of a function call so that the function does not
have to repeat expensive work.

The first time this runs:

```python
model = get_model()
```

the model is loaded.

The next time this runs:

```python
model = get_model()
```

the already-loaded model is returned from memory.

The model is loaded once per Python process.

---

## Why do we need `lru_cache`?

Loading a machine-learning model is expensive. It may require:

- Reading model files.
- Loading model weights.
- Initializing the tokenizer.
- Allocating memory.

Without `lru_cache`, the model could be loaded repeatedly:

```python
def encode_text(text: str) -> list[float]:
    model = SentenceTransformer(settings.MODEL_NAME)
    return model.encode(text).tolist()
```

If 100 requests call this function, the model may be loaded 100 times. This
would be slow and waste memory.

With `lru_cache`:

```text
First request  -> load model
Later requests -> reuse existing model
```

---

## `encode_text()`

```python
def encode_text(text: str) -> list[float]:
    return get_model().encode(
        text,
        normalize_embeddings=True,
    ).tolist()
```

This function performs three main steps:

1. Gets the cached model.
2. Converts the text into an embedding.
3. Converts the result into a normal Python list.

The option:

```python
normalize_embeddings=True
```

normalizes the vector, which is useful for similarity comparisons.

The `.tolist()` call converts the model's result into a regular Python list so it
can be stored in a database or serialized in an API response.

---

## `encode_note()`

```python
def encode_note(title: str, content: str) -> list[float]:
    return encode_text(f"{title}\n{content}")
```

This combines the title and content into one string.

For example:

```python
title = "Async Sessions"
content = "AsyncSession allows non-blocking database operations."
```

The function creates:

```text
Async Sessions
AsyncSession allows non-blocking database operations.
```

It then sends this complete text to `encode_text()`.

Both the title and content are included so that searches can match either the
title, the content, or the overall meaning of the note.

The same composition should be used when creating and updating notes. Otherwise,
the stored embedding may not represent the current note correctly.

---

## `encode_query()`

```python
def encode_query(query: str) -> list[float]:
    return encode_text(query)
```

This converts a user's search query into an embedding.

For example:

```python
query = "How do asynchronous database sessions work?"
```

The query is converted into a vector and compared with stored note vectors.

---

## Example: processing a note

Suppose the application receives:

```python
title = "Python APIs"
content = "FastAPI is used to build web APIs."
```

The application calls:

```python
embedding = encode_note(title, content)
```

The flow is:

```text
title + content
        |
        v
"Python APIs\nFastAPI is used to build web APIs."
        |
        v
encode_text(...)
        |
        v
get_model()
        |
        v
Load model if it is the first call
        |
        v
Reuse cached model if it was already loaded
        |
        v
model.encode(...)
        |
        v
Normalize the vector
        |
        v
Convert the result to a Python list
        |
        v
Return a 384-value embedding vector
```

The result may look conceptually like:

```python
[
    0.018,
    -0.093,
    0.221,
    ...
]
```

The complete result contains 384 numbers.

---

## Synchronous core functions

These functions are synchronous:

```python
encode_text()
encode_note()
encode_query()
```

They perform the actual embedding work.

For example:

```python
embedding = encode_note(title, content)
```

The function runs directly and returns the result.

The model's `encode()` method can take noticeable CPU time, especially when
processing many or long texts.

---

## What is a thread pool?

A thread pool is a group of background threads that can perform blocking or
time-consuming synchronous work.

FastAPI uses an underlying asynchronous event loop. The event loop is responsible
for handling many requests efficiently.

If a slow synchronous function runs directly inside the event loop, it can block
other requests.

---

## `run_in_threadpool()`

```python
from fastapi.concurrency import run_in_threadpool
```

`run_in_threadpool()` runs a normal synchronous function in a background thread.

For example:

```python
return await run_in_threadpool(
    encode_note,
    title,
    content,
)
```

This means:

```text
Run encode_note(title, content)
in a background thread,
then return its result asynchronously.
```

---

## `aencode_note()`

```python
async def aencode_note(title: str, content: str) -> list[float]:
    return await run_in_threadpool(
        encode_note,
        title,
        content,
    )
```

This is an asynchronous wrapper around the synchronous `encode_note()` function.

The actual encoding logic remains in:

```python
encode_note()
```

The wrapper only moves that work to a background thread.

You can call it from an async FastAPI function like this:

```python
embedding = await aencode_note(
    title="Python APIs",
    content="FastAPI is used to build web APIs.",
)
```

---

## `aencode_query()`

```python
async def aencode_query(query: str) -> list[float]:
    return await run_in_threadpool(
        encode_query,
        query,
    )
```

This works the same way, but it is intended for search queries.

Example:

```python
query_embedding = await aencode_query(
    "How do I build a Python API?"
)
```

The query encoding runs in a background thread so the main async event loop
remains available for other requests.

---

## Why use a thread pool?

Without the thread pool, an async route might call:

```python
embedding = encode_note(title, content)
```

The encoding work would run directly inside the async request handler.

If encoding takes time, the event loop may be blocked:

```text
Request 1 starts encoding
Request 1 blocks the event loop
Other requests must wait
```

With the thread pool:

```text
Request 1 starts encoding in a background thread
The event loop remains available
Other requests can continue
```

This is useful because `SentenceTransformer.encode()` is synchronous and may be
computationally expensive.

---

## Complete engineering flow

For a note:

```text
FastAPI route
    |
    v
await aencode_note(...)
    |
    v
run_in_threadpool(...)
    |
    v
encode_note(...)
    |
    v
encode_text(...)
    |
    v
get_model()
    |
    v
Load model once or reuse cached model
    |
    v
Generate normalized embedding
    |
    v
Return Python list
```

For a search query:

```text
FastAPI search route
    |
    v
await aencode_query(...)
    |
    v
run_in_threadpool(...)
    |
    v
encode_query(...)
    |
    v
encode_text(...)
    |
    v
Reuse cached model
    |
    v
Generate normalized query embedding
    |
    v
Search the database using the vector
```

---

## Summary

- `get_model()` loads the embedding model.
- `@lru_cache` ensures the model is loaded only once per process.
- `encode_text()` converts text into a normalized vector.
- `encode_note()` combines a note's title and content before encoding.
- `encode_query()` encodes a user's search query.
- `run_in_threadpool()` moves synchronous model work away from the async event
  loop.
- `aencode_note()` and `aencode_query()` provide asynchronous interfaces for
  FastAPI.

The design separates:

```text
Core embedding logic
        +
FastAPI-friendly async wrappers
```

This keeps the embedding functions reusable while preventing model inference
from blocking the FastAPI event loop.