from google import genai
from mcp.server.fastmcp import FastMCP
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pinecone import Pinecone
from dotenv import load_dotenv
import time
import os

from utils.logger_utils import create_logger

logger = create_logger("mcp_logger", "mcp.log")

load_dotenv()

PINECONE_API = os.getenv("PINECONE_API")
GOOGLE_API = os.getenv("GOOGLE_API")
INDEX_NAME = "giki-rag-app-db"  

pc = Pinecone(api_key=PINECONE_API)
index = pc.Index(INDEX_NAME)


mcp = FastMCP("giki-rag-app", host="0.0.0.0", port=8000)

def format_pinecone_results(results, max_chars=10000):
    """
    Format Pinecone query results into a single MCP-friendly string.
    Each match includes score, title, url, category, and a text snippet.
    """
    formatted_results = []

    # Handle both "matches" (old SDK) and "result.hits" (new SDK)
    matches = results.get("matches") or results.get("result", {}).get("hits", [])
    
    for match in matches:
        fields = match.get("fields", match.get("metadata", {}))
        score = round(match.get("_score", match.get("score", 0)), 3)

        title = fields.get("title", "[No title]")
        url = fields.get("url", "[No URL]")
        category = fields.get("category", "[No category]")
        content = fields.get("content", "[No text metadata]")

        # Truncate long content for readability
        snippet = content[:max_chars] + ("..." if len(content) > max_chars else "")

        formatted_results.append(
            f"Score: {score}\n"
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"URL: {url}\n"
            f"Text: {snippet}"
        )

    return "\n---\n".join(formatted_results)


@mcp.tool()
def pinecone_query(query: str, top_k: int = 3):

    """
    Use this tool to search information using Pinecone API

    Args:
        query: the search query
    
    Returns:
        The top-k search results
    """


    start_query = time.time()
    try:
        results = index.search(
            namespace="ai-lab",
            query={
                "inputs": {"text": query},
                "top_k": top_k
            }            
        )
    except Exception as e:
        logger.error(f"Pinecone Query Failed: {e}")
        return f"Error during Query: {e}"
    end_query = time.time()
    logger.info(f"Pinecone Query Time: {end_query - start_query:.4f}s")
    
    return format_pinecone_results(results) 


@mcp.tool()
def ai_chat(query: str):
    
    pinecone_results = pinecone_query(query)

     # Step 2: Summarize / Generate response using Gemini
    prompt = f"Given the following context from GIKI resources:\n{pinecone_results}\nAnswer the user's query concisely:\n{query}"

    # Initialize Gemini client
    client = genai.Client(api_key=GOOGLE_API)
    
    start_llm = time.time()
    # Generate response using Gemini
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    end_llm = time.time()
    logger.info(f"Total Time Taken by Gemini: {end_llm - start_llm:.4f}s")

    return response.text


if __name__ == "__main__":
    mcp.run(transport="streamable-http")


