from fastapi import FastAPI

# Create the FastAPI application instance
app = FastAPI()

# Define a route for the root URL using a GET method
@app.get("/")
def read_root():
    return {"Hello": "World"}

# Define a route with a path parameter and an optional query parameter
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}