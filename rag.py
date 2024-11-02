import os
from fastapi import APIRouter
from openai import OpenAI
from qdrant_client import QdrantClient
from config import OPENAI_API_KEY
import uuid
client = OpenAI(api_key=OPENAI_API_KEY)
# Qdrantクライアントの初期化
qdrant = QdrantClient(url="http://localhost:6333")

# コレクション名の定義
COLLECTION_NAME = "knowledge_base"

router = APIRouter()


@router.post("/knowledge")
async def add_knowledge(text: str):
    # embeddingを取得
    embedding = client.embeddings.create(
        input=text, model="text-embedding-3-small").data[0].embedding

    # Qdrantにコレクションが存在しない場合は作成
    collections = qdrant.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "size": len(embedding),
                "distance": "Cosine"
            }
        )

    # ベクトルとテキストをQdrantに保存
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[{
            "id": str(uuid.uuid4()),
            "vector": embedding,
            "payload": {"text": text}
        }]
    )

    return {"status": "success"}


def get_knowledges(text: str):
    embedding = client.embeddings.create(
        input=text, model="text-embedding-3-small").data[0].embedding
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=3
    )
    return [{"text": r.payload["text"], "score": r.score} for r in results]


@router.post("/knowledge_search")
async def knowledge_search(text: str):
    knowledges = get_knowledges(text)
    return knowledges
