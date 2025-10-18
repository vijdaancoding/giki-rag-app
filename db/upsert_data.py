from sentence_transformers import SentenceTransformer
from hashlib import sha1
from pinecone import Pinecone
from dotenv import load_dotenv
import os

load_dotenv()

PINECONE_API = os.getenv("PINECONE_API")

from .cleaning.clean_text import clean_entire_result

model = SentenceTransformer("all-MiniLM-L6-v2")

json_path = "data/crawl_result.json"
data = clean_entire_result(json_path)

texts = [item["content"] for item in data if item.get("content")]
embeddings = model.encode(texts, batch_size=16, show_progress_bar=True)

def stable_id(url: str) -> str:
    return sha1(url.encode("utf-8")).hexdigest()

records = []
for item, vector in zip(data, embeddings):
    records.append({
        "id": stable_id(item["url"]),
        "values": vector.tolist(),  # convert NumPy array → list
        "metadata": {
            "url": item["url"],
            "title": item["metadata"].get("title"),
            "crawled_at": item["crawled_at"],
            "content": item["content"]
        }
    })

pc = Pinecone(api_key=PINECONE_API)
index = pc.Index("giki-crawl")

BATCH_SIZE = 16

for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i+BATCH_SIZE]
    index.upsert(vectors=batch)

