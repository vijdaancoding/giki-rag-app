from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from dotenv import load_dotenv
from typing import Dict, List
import time
import logging
import os

from utils.logger_utils import create_logger

logger = create_logger("mcp_logger", "mcp.log")

load_dotenv()

PINECONE_API = os.getenv("PINECONE_API")
INDEX_NAME = "giki-crawl"  

pc = Pinecone(api_key=PINECONE_API)
index = pc.Index(INDEX_NAME)

embedder = SentenceTransformer("all-MiniLM-L6-v2")

mcp = FastMCP("giki-rag-app")

@mcp.tool()
def pinecone_query(query: str, top_k: int = 5):

    """
    Use this tool to search information using Pinecone API

    Args:
        query: the search query
    
    Returns:
        The top-k search results
    """

    start_embed = time.time()
    query_vector = embedder.encode(query).tolist()
    end_embed = time.time()
    logger.info(f"Embedding Time for Query: {query} | {end_embed - start_embed:.4f}s")

    start_query = time.time()
    try:
        results = index.query(vector=query_vector, 
                              top_k=top_k, 
                              include_metadata=True)
    except Exception as e:
        logger.error(f"Pinecone Query Failed: {e}")
        return f"Error during Query: {e}"
    end_query = time.time()
    logger.info(f"Pinecone Query Time: {end_query - start_query:.4f}s")

    if not results or "matches" not in results:
        return "No results found or query failed"

    formatted_results = []
    for match in results["matches"]:
        meta = match.get("metadata", {})
        text_snippet = meta.get("content", "[No text metadata]")
        score = round(match.get("score", 0), 3)
        formatted_results.append(f"Score: {score}\nText: {text_snippet}")

    return "\n---\n".join(formatted_results)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")


