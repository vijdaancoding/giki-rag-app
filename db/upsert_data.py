from hashlib import sha1
from pinecone import Pinecone
from dotenv import load_dotenv
import os
from typing import Dict, List
import math
from tqdm import tqdm


load_dotenv()

PINECONE_API = os.getenv("PINECONE_API")

from .cleaning.parse_data import main as cleaning_entire_data 

pc = Pinecone(api_key=PINECONE_API)
index = pc.Index("giki-rag-app-db")


def chunk_records(records: List[Dict], batch_size: int = 30):
    """Yield successive batches of records."""
    for i in range(0, len(records), batch_size):
        yield records[i:i + batch_size]


def upsert_batched(records: List[Dict], namespace: str, batch_size: int = 30):
    """Upload records to Pinecone in small batches."""
    total_batches = math.ceil(len(records) / batch_size)
    print(f"📤 Uploading {len(records)} records in {total_batches} batches of {batch_size}...")

    for i, batch in enumerate(tqdm(chunk_records(records, batch_size))):
        try:
            index.upsert_records(namespace=namespace, records=batch)
        except Exception as e:
            print(f"⚠️ Batch {i+1} failed: {e}")
            continue


if __name__ == "__main__":
    records = cleaning_entire_data()
    upsert_batched(records, namespace="ai-lab", batch_size=30)
    print("✅ All batches uploaded successfully!")

