# Embedding Service

This file explains how the embedding service works and how it is used to
generate vector embeddings for notes and search queries.

The embedding service is responsible for:

- Loading the sentence-transformer model.
- Loading the model only once.
- Checking that the model dimension matches the database vector column.
- Converting text into normalized embedding vectors.
- Creating embeddings for notes.
- Creating embeddings for search queries.
- Ensuring that note creation and note updates use the same text format.

---

## Complete code

```python
import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


logger = logging.getLogger(__name__)


EXPECTED_DIM = 384  # Must match Vector(384) in the database model


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


def encode_text(text: str) -> list[float]:
    return get_model().encode(
        text,
        normalize_embeddings=True,
    ).tolist()


def encode_note(title: str, content: str) -> list[float]:
    """
    Create one embedding from both the note title and note content.

    The same text composition must be used when creating and updating notes.
    """
    return encode_text(f"{title}\n{content}")


def encode_query(query: str) -> list[float]:
    return encode_text(query)
```

---

## What is an embedding?

An embedding is a list of numbers representing the meaning of text.

For example, this note:

```text
Title: Async database sessions

Content: AsyncSession allows database operations without blocking the event loop.
```

is converted into a numerical vector:

```python
[
    0.021,
    -0.104,
    0.087,
    ...
]
```

The vector contains `384` floating-point numbers when using a model that
produces 384-dimensional embeddings.

Text with similar meanings should produce vectors that are close to each other.

For example:

```text
"How do async database sessions work?"
```

and:

```text
"Explain asynchronous DB sessions."
```

may use different words, but their embeddings should be semantically similar.

This makes embeddings useful for semantic search.

---

## Why use `SentenceTransformer`?

The following import provides the sentence-transformer model:

```python
from sentence_transformers import SentenceTransformer
```

`SentenceTransformer` is used to convert text into embeddings.

The model can encode:

- Sentences
- Paragraphs
- Notes
- Documents
- Search queries

The actual model is selected through the application configuration:

```python
settings.MODEL_NAME
```

For example, the configuration may contain:

```env
MODEL_NAME=all-MiniLM-L6-v2
```

This keeps the model name outside the service code. You can change the model
through environment configuration without changing the Python implementation.

---

## Logging setup

```python
import logging

logger = logging.getLogger(__name__)
```

This creates a logger for the current module.

Logging is useful because loading a machine-learning model can take time and may
use a significant amount of memory.

The service logs important events:

```python
logger.info("Loading embedding model: %s ...", settings.MODEL_NAME)
```

This tells us that model loading has started.

After loading, it logs:

```python
logger.info("Embedding model ready (dim=%d)", dim)
```

This confirms that the model loaded successfully and shows the model's vector
dimension.

Using logging is better than using `print()` because logging supports:

- Different log levels
- Production log collection
- Timestamps
- Log files
- Debugging
- Monitoring systems

---

## The `EXPECTED_DIM` constant

```python
EXPECTED_DIM = 384
```

This represents the number of values in each embedding vector expected by the
application.

The value must match the vector dimension defined in the database model.

For example, a SQLModel model may contain:

```python
from pgvector.sqlalchemy import Vector


embedding: list[float] = Field(
    sa_type=Vector(384),
    nullable=False,
)
```

The database column in this case is equivalent to:

```text
vector(384)
```

That means the database expects exactly 384 floating-point values.

---

## Why the vector dimension must match

Suppose the model produces a vector with 384 values:

```python
[0.1, 0.2, ..., 0.384]
```

Then the database column must be:

```text
vector(384)
```

If the model produces 768 values but the database column expects 384, the insert
will fail.

For example:

```text
Model output: 768 dimensions
Database column: vector(384)
```

These values are incompatible.

The embedding model and database column must agree:

```text
Embedding model dimension == Database vector dimension
```

This code checks that relationship:

```python
dim = model.get_embedding_dimension()

if dim != EXPECTED_DIM:
    logger.warning(
        "Model dim=%d but DB column is vector(%d) — inserts will fail!",
        dim,
        EXPECTED_DIM,
    )
```

The warning helps detect configuration mistakes early.

---

## Why use a warning instead of raising an exception?

The current code logs a warning:

```python
logger.warning(...)
```

This allows the application to finish loading, but it warns that inserts may
fail later.

This can be useful during development because you can inspect the warning and
fix the configuration.

However, for production, you may prefer to fail immediately:

```python
if dim != EXPECTED_DIM:
    raise ValueError(
        f"Embedding dimension mismatch: "
        f"model={dim}, database={EXPECTED_DIM}"
    )
```

Failing immediately is often safer because the application will not start with
an invalid embedding configuration.

A stricter version could be:

```python
@lru_cache
def get_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s ...", settings.MODEL_NAME)

    model = SentenceTransformer(settings.MODEL_NAME)
    dim = model.get_embedding_dimension()

    if dim != EXPECTED_DIM:
        raise ValueError(
            f"Model dimension is {dim}, but the database expects "
            f"{EXPECTED_DIM} dimensions."
        )

    logger.info("Embedding model ready (dim=%d)", dim)

    return model
```

---

## The `get_model()` function

```python
@lru_cache
def get_model() -> SentenceTransformer:
```

This function loads and returns the embedding model.

The important part is the decorator:

```python
@lru_cache
```

`lru_cache` stores the result of a function call.

When `get_model()` is called for the first time:

```python
model = get_model()
```

the function:

1. Loads the model.
2. Checks its dimension.
3. Logs that the model is ready.
4. Returns the model.
5. Stores the returned model in the cache.

When `get_model()` is called again, the cached model is returned instead of
loading the model again.

---

## Why use `@lru_cache`?

Loading a sentence-transformer model is expensive.

It may require:

- Reading model files from disk.
- Loading neural-network weights.
- Loading tokenizer files.
- Initializing the runtime.
- Allocating memory.
- Detecting CPU or GPU support.

Without caching, this would be inefficient:

```python
def encode_text(text: str) -> list[float]:
    model = SentenceTransformer(settings.MODEL_NAME)
    return model.encode(text).tolist()
```

Every call to `encode_text()` could load the model again.

That would cause:

- Slow requests.
- High memory usage.
- Unnecessary disk reads.
- Poor application performance.
- Possible out-of-memory errors.

With `@lru_cache`, the model is loaded once per Python process.

```python
@lru_cache
def get_model():
    return SentenceTransformer(settings.MODEL_NAME)
```

All later calls reuse the same model instance.

---

## What does “once” mean?

The model is loaded once per Python process.

If you run one application process:

```text
1 process = 1 model instance
```

If you run four workers:

```bash
uvicorn app.main:app --workers 4
```

then each worker is a separate process:

```text
4 workers = 4 model instances
```

This may increase memory usage.

The cache does not share the model between different processes. It only prevents
repeated loading within the same process.

---

## How the cache works

The first call:

```python
model_one = get_model()
```

loads the model.

The second call:

```python
model_two = get_model()
```

returns the cached model.

Conceptually:

```python
model_one is model_two
```

will normally be:

```python
True
```

Both variables point to the same model object.

---

## Clearing the model cache

`lru_cache` provides a method to clear the cached model:

```python
get_model.cache_clear()
```

This can be useful in tests or when changing configuration at runtime.

Example:

```python
get_model.cache_clear()
```

After clearing the cache, the next call to `get_model()` loads the model again.

Normally, you should not clear the cache during regular application operation.

---

## The `encode_text()` function

```python
def encode_text(text: str) -> list[float]:
    return get_model().encode(
        text,
        normalize_embeddings=True,
    ).tolist()
```

This function converts text into a Python list of floating-point numbers.

The operation happens in several steps.

### Step 1: Get the cached model

```python
get_model()
```

This loads the model on the first call and returns the cached model afterward.

### Step 2: Encode the text

```python
get_model().encode(text)
```

The model converts the text into an embedding vector.

### Step 3: Normalize the embedding

```python
normalize_embeddings=True
```

This normalizes the vector.

### Step 4: Convert the result to a list

```python
.tolist()
```

This converts the result into a normal Python list.

---

## Why normalize embeddings?

The code uses:

```python
normalize_embeddings=True
```

Normalization changes the vector so that its length is approximately `1`.

This is useful when comparing vectors with cosine similarity.

Without normalization, vector magnitude can affect similarity calculations.

With normalization, the comparison focuses more on the direction of the vectors,
which generally represents semantic similarity.

For example:

```text
Note vector:  [0.2, 0.5, 0.1, ...]
Query vector: [0.3, 0.7, 0.2, ...]
```

Normalization makes similarity comparisons more consistent.

---

## Normalization must be consistent

If note embeddings are normalized, query embeddings should also be normalized.

This code does that automatically because both functions call `encode_text()`:

```python
def encode_note(title: str, content: str) -> list[float]:
    return encode_text(f"{title}\n{content}")


def encode_query(query: str) -> list[float]:
    return encode_text(query)
```

Both note vectors and query vectors use:

```python
normalize_embeddings=True
```

This is important for reliable semantic search.

---

## Why call `.tolist()`?

The result from `model.encode()` may be a NumPy array.

For example:

```python
array([0.12, -0.03, 0.44, ...])
```

A NumPy array is useful for numerical calculations, but it may not be directly
compatible with:

- JSON responses.
- Pydantic serialization.
- Database drivers.
- pgvector fields.
- API response bodies.

Calling:

```python
.tolist()
```

converts it into a normal Python list:

```python
[0.12, -0.03, 0.44, ...]
```

This makes the embedding easier to store and pass through the application.

---

## The `encode_note()` function

```python
def encode_note(title: str, content: str) -> list[float]:
    """
    Single composition used by BOTH create and update — never inline this f-string elsewhere.
    """
    return encode_text(f"{title}\n{content}")
```

This function combines the note title and note content into one string and then
creates an embedding from that combined text.

For example:

```python
title = "Async database sessions"
content = "AsyncSession allows non-blocking database operations."
```

The function creates:

```text
Async database sessions
AsyncSession allows non-blocking database operations.
```

The newline comes from:

```python
f"{title}\n{content}"
```

The combined text is then passed to:

```python
encode_text(...)
```

---

## Why include both the title and content?

The title often contains important information about the note.

For example:

```text
Title: Python database migrations
Content: Use Alembic to manage schema changes.
```

If only the content were embedded, the search system might lose the importance
of the title.

By embedding both fields, a search for:

```text
How do I manage database migrations?
```

can match:

- The title.
- The content.
- The combined meaning of the note.

The title and content are treated as one semantic document.

---

## Why use a newline between title and content?

The function uses:

```python
f"{title}\n{content}"
```

instead of:

```python
f"{title} {content}"
```

The newline makes the boundary between the title and content clear.

For example:

```text
Async database sessions
AsyncSession allows non-blocking database operations.
```

is easier to understand than:

```text
Async database sessions AsyncSession allows non-blocking database operations.
```

The model can process either version, but the newline provides a clean and
consistent composition format.

The most important thing is to use the same composition format every time.

---

## Why the composition must be centralized

The docstring says:

```python
Single composition used by BOTH create and update —
never inline this f-string elsewhere.
```

This is an important engineering rule.

The title and content should always be combined in exactly the same way when:

- Creating a note.
- Updating a note.
- Rebuilding embeddings.
- Importing notes.
- Repairing missing embeddings.

Correct:

```python
embedding = encode_note(note.title, note.content)
```

Avoid repeating the formatting in different files:

```python
embedding = encode_text(f"{title}\n{content}")
```

If the format is duplicated in multiple places, one file may eventually change
without changing the others.

For example, creation may use:

```python
f"{title}\n{content}"
```

while update accidentally uses:

```python
f"{content}\n{title}"
```

The resulting vectors would be generated from different text formats.

Centralizing the composition avoids this problem.

---

## Why create and update must use the same encoding

Suppose a note is created with:

```python
embedding = encode_note(title, content)
```

Later, the content is updated.

The embedding must be regenerated:

```python
embedding = encode_note(updated_title, updated_content)
```

If the embedding is not updated, the database contains:

```text
Current note content
Old note embedding
```

The search results may then be incorrect.

For example:

1. A note originally discusses FastAPI.
2. The note is updated to discuss PostgreSQL.
3. The content changes, but the embedding remains about FastAPI.
4. A search for PostgreSQL does not find the note correctly.
5. A search for FastAPI may incorrectly return the note.

Therefore, whenever title or content changes, regenerate the embedding.

---

## Example note creation

```python
from app.services.embeddings import encode_note


async def create_note(
    session: AsyncSession,
    note_in: NoteCreate,
) -> Note:
    embedding = encode_note(
        title=note_in.title,
        content=note_in.content,
    )

    db_note = Note(
        title=note_in.title,
        content=note_in.content,
        embedding=embedding,
    )

    session.add(db_note)

    await session.commit()
    await session.refresh(db_note)

    return db_note
```

The process is:

```text
1. Receive the title and content.
2. Combine the title and content.
3. Generate the embedding.
4. Store the note and embedding.
5. Commit the transaction.
```

---

## Example note update

```python
from app.services.embeddings import encode_note


async def update_note(
    session: AsyncSession,
    note_id: UUID,
    updates: NoteUpdate,
) -> Note:
    note = await get_note_by_id(session, note_id)

    if not note:
        raise ValueError("Note not found")

    data = updates.model_dump(exclude_unset=True)

    note.sqlmodel_update(data)

    if "title" in data or "content" in data:
        note.embedding = encode_note(
            title=note.title,
            content=note.content,
        )

    await session.commit()
    await session.refresh(note)

    return note
```

The embedding is regenerated only when the title or content changes.

This avoids unnecessarily encoding the note when updating unrelated fields.

---

## The `encode_query()` function

```python
def encode_query(query: str) -> list[float]:
    return encode_text(query)
```

This function converts a user's search query into an embedding.

For example:

```python
query_embedding = encode_query(
    "How do I use async database sessions?"
)
```

Internally, it calls:

```python
encode_text(query)
```

Therefore, query embeddings use:

- The same model.
- The same normalization.
- The same output format.
- The same vector dimension.

---

## Why have both `encode_note()` and `encode_query()`?

Although `encode_query()` currently delegates to `encode_text()`, it has a
different responsibility from `encode_note()`.

### `encode_note()`

Used for stored content:

```python
note_embedding = encode_note(
    title=note.title,
    content=note.content,
)
```

### `encode_query()`

Used for temporary user search input:

```python
query_embedding = encode_query(user_query)
```

These functions are separate because notes and queries represent different
concepts in the application.

---

## Engineering reason 1: Clear intent

This is more expressive:

```python
note_embedding = encode_note(title, content)
query_embedding = encode_query(query)
```

Compared with:

```python
note_embedding = encode_text(note_text)
query_embedding = encode_text(query)
```

The first version makes the purpose clear immediately.

The reader does not have to guess whether a string is:

- A stored note.
- A user query.
- A document.
- A title.
- A paragraph.

---

## Engineering reason 2: Future flexibility

Some embedding models use different instructions for documents and queries.

For example, a model may expect:

```text
passage: FastAPI is a Python web framework.
```

for stored content and:

```text
query: How does FastAPI work?
```

for search queries.

If that becomes necessary, the functions can change independently:

```python
def encode_note(title: str, content: str) -> list[float]:
    text = f"passage: {title}\n{content}"
    return encode_text(text)


def encode_query(query: str) -> list[float]:
    return encode_text(f"query: {query}")
```

The rest of the application does not need to change.

---

## Engineering reason 3: Separate preprocessing

In the future, note text and query text may require different preprocessing.

For example:

```python
def encode_note(title: str, content: str) -> list[float]:
    title = title.strip()
    content = content.strip()

    return encode_text(f"{title}\n{content}")


def encode_query(query: str) -> list[float]:
    query = query.strip()

    return encode_text(query)
```

Keeping separate functions makes this distinction explicit.

---

## Engineering reason 4: Better testing

Separate functions make it easier to test the intended behavior:

```python
def test_encode_note_dimension():
    embedding = encode_note(
        title="Database",
        content="PostgreSQL supports vector search.",
    )

    assert len(embedding) == EXPECTED_DIM
```

```python
def test_encode_query_dimension():
    embedding = encode_query(
        "How does vector search work?"
    )

    assert len(embedding) == EXPECTED_DIM
```

If the implementation later becomes different, the tests remain clear.

---

## Engineering reason 5: Better observability

Separate functions also make logging and performance monitoring easier.

You could measure:

- How long note embeddings take.
- How long query embeddings take.
- How many notes are encoded.
- How many searches are performed.
- Whether note encoding is failing.
- Whether query encoding is failing.

This distinction can be useful when optimizing the application.

---

## Why not combine everything into one function?

You could write:

```python
def encode(value: str) -> list[float]:
    return get_model().encode(
        value,
        normalize_embeddings=True,
    ).tolist()
```

This is technically valid.

However, it removes useful domain information:

```python
embedding = encode(value)
```

It is not immediately clear what `value` represents.

The current design gives the application a more meaningful interface:

```python
note_embedding = encode_note(title, content)
query_embedding = encode_query(query)
```

The implementation is shared where appropriate, while the public functions
communicate their purpose.

---

## Semantic search flow

The complete search flow is:

```text
User enters a search query
            |
            v
encode_query(query)
            |
            v
Query embedding vector
            |
            v
Compare query vector with note vectors
            |
            v
Rank notes by similarity
            |
            v
Return the most relevant notes
```

When a note is created:

```text
Note title + content
            |
            v
encode_note(title, content)
            |
            v
Note embedding vector
            |
            v
Store note and vector in the database
```

When a note is updated:

```text
Updated title/content
            |
            v
encode_note(updated_title, updated_content)
            |
            v
Replace the old embedding
            |
            v
Commit the updated note
```

---

## Validation and error handling

The current functions do not validate empty values:

```python
def encode_text(text: str) -> list[float]:
    return get_model().encode(
        text,
        normalize_embeddings=True,
    ).tolist()
```

You may want to add validation:

```python
def encode_text(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    return get_model().encode(
        text,
        normalize_embeddings=True,
    ).tolist()
```

This prevents meaningless or invalid embeddings from being generated for empty
strings.

You may also add validation to `encode_note()`:

```python
def encode_note(title: str, content: str) -> list[float]:
    if not title.strip() and not content.strip():
        raise ValueError("A note must contain a title or content")

    return encode_text(f"{title}\n{content}")
```

---

## A more defensive version

```python
import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


logger = logging.getLogger(__name__)


EXPECTED_DIM = 384


@lru_cache
def get_model() -> SentenceTransformer:
    logger.info(
        "Loading embedding model: %s ...",
        settings.MODEL_NAME,
    )

    model = SentenceTransformer(settings.MODEL_NAME)
    dim = model.get_embedding_dimension()

    if dim != EXPECTED_DIM:
        raise ValueError(
            f"Model dimension is {dim}, but the database expects "
            f"{EXPECTED_DIM} dimensions."
        )

    logger.info(
        "Embedding model ready (dim=%d)",
        dim,
    )

    return model


def encode_text(text: str) -> list[float]:
    """
    Convert text into a normalized embedding vector.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    embedding = get_model().encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()


def encode_note(title: str, content: str) -> list[float]:
    """
    Generate an embedding from a note's title and content.

    This composition must be used consistently during note creation,
    note updates, imports, and embedding rebuilds.
    """
    if not title.strip() and not content.strip():
        raise ValueError(
            "A note must contain a title or content"
        )

    note_text = f"{title}\n{content}"

    return encode_text(note_text)


def encode_query(query: str) -> list[float]:
    """
    Generate an embedding from a user's search query.
    """
    return encode_text(query)
```

---

## Synchronous model inference

`SentenceTransformer.encode()` is a synchronous function:

```python
model.encode(text)
```

Therefore, this is correct:

```python
embedding = encode_text(text)
```

This is incorrect:

```python
embedding = await encode_text(text)
```

The function is not declared with `async def`, so it does not return an
awaitable coroutine.

However, model inference can be CPU-intensive. In an async FastAPI application,
long-running synchronous inference can block the event loop.

For heavier workloads, you can run it in a worker thread:

```python
import asyncio


async def encode_text_async(text: str) -> list[float]:
    return await asyncio.to_thread(
        encode_text,
        text,
    )
```

Then use:

```python
embedding = await encode_text_async(note.content)
```

Whether this is necessary depends on:

- Model size.
- CPU speed.
- GPU availability.
- Number of concurrent users.
- Length of input text.
- Required response latency.

For small local projects, the synchronous function may be sufficient.

---

## Batch encoding

When generating embeddings for many notes, use batch encoding where possible.

A batch function could look like this:

```python
def encode_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    embeddings = get_model().encode(
        texts,
        normalize_embeddings=True,
    )

    return embeddings.tolist()
```

This is useful for:

- Seed scripts.
- Bulk imports.
- Rebuilding all note embeddings.
- Migrating to a new model.
- Processing documents in batches.

Example:

```python
texts = [
    "FastAPI is a Python framework.",
    "SQLModel works with SQLAlchemy.",
    "PostgreSQL supports vector search.",
]

embeddings = encode_texts(texts)
```

Batch processing is often faster than calling the model separately for every
individual text.

---

## Database requirements

The database vector column must match the model dimension.

If:

```python
EXPECTED_DIM = 384
```

then the database model should use:

```python
Vector(384)
```

Example:

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class Note(SQLModel, table=True):
    id: UUID = Field(primary_key=True)

    title: str
    content: str

    embedding: list[float] = Field(
        sa_column=Column(Vector(384), nullable=False)
    )
```

The exact model definition may differ depending on the SQLModel and pgvector
versions being used.

The important relationship is:

```text
EXPECTED_DIM = Vector column dimension = Model output dimension
```

---

## What happens if the model changes?

If you change the model:

```env
MODEL_NAME=some-other-model
```

the new model may produce a different vector dimension.

For example:

```text
Old model: 384 dimensions
New model: 768 dimensions
```

Changing the model requires more than changing the environment variable.

You may need to:

1. Update `EXPECTED_DIM`.
2. Update the database vector column.
3. Create a new migration.
4. Re-encode all existing notes.
5. Rebuild any vector indexes.
6. Re-run search evaluation tests.

Vectors generated by different models should not normally be compared directly.

---

## Important consistency rules

For reliable semantic search:

1. Use the same model for stored notes and search queries.
2. Use the same vector dimension.
3. Use the same normalization setting.
4. Use the same title/content composition.
5. Regenerate embeddings after title or content changes.
6. Do not mix vectors from incompatible models.
7. Rebuild embeddings when changing models.
8. Keep embedding logic in one service module.

---

## Summary

This embedding service provides a central place for all vector-generation
logic.

### `get_model()`

```python
get_model()
```

- Loads the model.
- Caches it with `@lru_cache`.
- Checks its embedding dimension.
- Returns the shared model instance.

### `encode_text()`

```python
encode_text(text)
```

- Converts text into an embedding.
- Normalizes the vector.
- Converts it into a Python list.

### `encode_note()`

```python
encode_note(title, content)
```

- Combines the note title and content.
- Generates one embedding for the complete note.
- Ensures creation and update use the same format.

### `encode_query()`

```python
encode_query(query)
```

- Converts a user's search query into an embedding.
- Uses the same model and normalization as note embeddings.

The most important design decisions are:

```text
Load the model once.
Keep the vector dimension consistent.
Use the same encoding process for note creation and updates.
Use normalized vectors for consistent similarity comparisons.
Keep note encoding and query encoding as separate domain functions.
```