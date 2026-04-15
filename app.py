from flask import Flask, jsonify, request
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Post:
    author: str
    title: str
    content: str
    id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data["id"],
            author=data["author"],
            title=data.get("title", ""),
            content=data.get("content", ""),
            created_at=data.get("created_at", ""),
        )


load_dotenv()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE = os.getenv("COSMOS_DATABASE")
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER")

app = Flask(__name__)
_client = None
_container = None


def get_container():
    global _client, _container
    if _container is None:
        _client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
        database = _client.get_database_client(COSMOS_DATABASE)
        _container = database.get_container_client(COSMOS_CONTAINER)
    return _container


# GET /
@app.route('/', methods=['GET'])
def home():
    return jsonify({'data': 'hello world'})


# GET /posts
@app.route('/posts', methods=['GET'])
def get_posts():
    container = get_container()
    results = container.query_items(
        query="SELECT * FROM c",
        enable_cross_partition_query=True
    )
    return [Post.from_dict(r) for r in results]


# GET /posts/id
@app.route('/posts/<int:id>', methods=['GET'])
def get_post(id):
    container = get_container()
    results = list(container.query_items(
        query='SELECT * FROM c WHERE c.id = @id',
        parameters=[{'name': '@id', 'value': str(id)}],
        enable_cross_partition_query=True
    ))
    return jsonify(Post.from_dict(results[0]).to_dict())


# POST /posts
# Request body: title, content, author
@app.route('/posts', methods=['POST'])
def create_post():
    container = get_container()
    content_type = request.headers.get('Content-Type')
    if content_type != 'application/json':
        return 'Content-Type not supported!'
    json = request.json
    post = Post(
        author=json.get("author"),
        title=json.get("title"),
        content=json.get("content"),
        id=json.get("id"))
    container.create_item(body=post.to_dict())
    return json


# DELETE /posts/id
@app.route('/posts', methods=['DELETE'])
def delete_post():
    container = get_container()
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        json = request.json
        container.delete_item(json.get("id"), partition_key=json.get("author"))
        return json
    else:
        return 'Content-Type not supported!'


if __name__ == '__main__':
    app.run(debug=True)
