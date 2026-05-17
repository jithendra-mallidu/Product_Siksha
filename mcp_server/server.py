#!/usr/bin/env python3
"""
PM Mentor MCP Server - RAG-powered PM interview coaching.

Exposes the PM Mentor agent as an MCP tool that can be called from
Claude Code, ChatGPT, Gemini, or any MCP-compatible client.

Connects directly to the vector DB and Claude API — no Flask backend needed.
"""

import json
import os
from pathlib import Path

import psycopg2
from anthropic import Anthropic
import google.generativeai as genai
from mcp.server.fastmcp import FastMCP

# Load .env from backend directory
BACKEND_DIR = Path(__file__).parent.parent / "backend"
ENV_FILE = BACKEND_DIR / ".env"

def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

VECTOR_DB_URL = os.environ.get("VECTOR_DB_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072

SYSTEM_PROMPT = """You are a PM Interview Mentor, an expert coach helping candidates prepare for Product Management interviews at top tech companies.

## Your Role
- Guide candidates through structured problem-solving, don't just give answers
- Use the Socratic method: ask probing questions to help them think deeper
- When they're stuck, provide hints rather than full solutions
- Validate good thinking and gently correct misconceptions
- Adapt your coaching style to their experience level

## How You Think
You do NOT default to any single framework for a question type. Instead:
- Read the retrieved knowledge base context carefully — it contains insights from PM interview books, articles, and real-world advice
- Let the context inform your approach. If the context suggests a particular framework fits well, use it. If multiple approaches are valid, present the tradeoffs and let the candidate choose
- Think from first principles about what the question actually demands before reaching for any methodology
- Different questions within the same category can require very different approaches — a "design a product for X" question is fundamentally different from "improve feature Y", even though both are Product Design
- Draw on specific insights, examples, and nuances from the retrieved context rather than giving generic advice

## Guidelines
- Help candidates structure their thinking, but don't force a rigid template
- Encourage specificity: real metrics, real user segments, real examples
- Push candidates to consider edge cases and tradeoffs
- If the retrieved context offers a relevant insight or contrarian take, surface it
- When no context is retrieved, coach from first principles rather than defaulting to a memorized framework

## Response Style
- Be encouraging but direct
- Use bullet points and structure for clarity
- Keep responses focused — don't overwhelm with everything at once
- If the candidate gives a good answer, acknowledge it and suggest how to make it even better
- If they're way off track, guide them back with questions rather than lecturing"""

# In-memory conversation store keyed by session_id
conversations: dict[str, list[dict]] = {}

mcp = FastMCP(
    "pm-mentor",
    instructions="PM Interview Mentor — practice PM interview questions with RAG-powered coaching from Lewis Lin's books and articles.",
)


def get_query_embedding(query: str) -> list[float] | None:
    if not GEMINI_API_KEY:
        return None
    genai.configure(api_key=GEMINI_API_KEY)
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=query,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
    return result["embedding"]


def retrieve_relevant_chunks(query: str, top_k: int = 5) -> list[dict]:
    if not VECTOR_DB_URL or not GEMINI_API_KEY:
        return []

    embedding = get_query_embedding(query)
    if not embedding:
        return []

    conn = psycopg2.connect(VECTOR_DB_URL)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT source_name, chunk_text, 1 - (embedding <=> %s::vector) as similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (str(embedding), str(embedding), top_k),
    )
    results = [
        {"source": row[0], "text": row[1], "similarity": float(row[2])}
        for row in cursor.fetchall()
    ]
    conn.close()
    return results


def build_context(question: str, category: str, company: str, chunks: list[dict]) -> str:
    parts = []
    if chunks:
        parts.append("## Relevant Knowledge Base Context")
        for chunk in chunks:
            if chunk["similarity"] > 0.3:
                parts.append(f"\n**From: {chunk['source']}**\n{chunk['text']}")
    parts.append("\n## Current Question")
    parts.append(f"**Category:** {category}")
    parts.append(f"**Company:** {company}")
    parts.append(f"**Question:** {question}")
    return "\n".join(parts)


@mcp.tool()
def mentor_chat(
    message: str,
    question: str = "",
    category: str = "General",
    company: str = "Unknown",
    session_id: str = "default",
) -> str:
    """Chat with the PM Interview Mentor for coaching on product management interview questions.

    Args:
        message: Your message or answer to discuss with the mentor
        question: The PM interview question you're practicing (set once per session)
        category: Question category - Product Design, Strategy, Execution/Metrics, Behavioral, Estimation, Technical
        company: Target company for the question (e.g. Google, Meta, Amazon)
        session_id: Session identifier to maintain conversation context across turns
    """
    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY not configured."

    history = conversations.get(session_id, [])

    search_query = f"{category} {question} {message}"
    chunks = retrieve_relevant_chunks(search_query)
    context = build_context(question, category, company, chunks)

    messages = []
    if not history:
        messages.append({
            "role": "user",
            "content": f"{context}\n\n---\n\nThe candidate says: {message}",
        })
    else:
        messages.append({
            "role": "user",
            "content": f"{context}\n\n---\n\nThe candidate says: {history[0]['content']}",
        })
        for msg in history[1:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    assistant_reply = response.content[0].text

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": assistant_reply})
    conversations[session_id] = history

    return assistant_reply


@mcp.tool()
def mentor_reset(session_id: str = "default") -> str:
    """Reset a mentor conversation to start fresh with a new question.

    Args:
        session_id: Session identifier to reset
    """
    if session_id in conversations:
        del conversations[session_id]
        return f"Session '{session_id}' cleared. Ready for a new question."
    return f"No active session '{session_id}' found."


@mcp.tool()
def mentor_search(query: str, top_k: int = 5) -> str:
    """Search the PM knowledge base directly for relevant content from Lewis Lin's books and articles.

    Args:
        query: Search query about PM interviews, frameworks, or concepts
        top_k: Number of results to return (default 5)
    """
    chunks = retrieve_relevant_chunks(query, top_k)
    if not chunks:
        return "No relevant content found. Check that VECTOR_DB_URL and GEMINI_API_KEY are configured."

    results = []
    for i, chunk in enumerate(chunks, 1):
        results.append(
            f"### Result {i} (similarity: {chunk['similarity']:.3f})\n"
            f"**Source:** {chunk['source']}\n\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(results)


if __name__ == "__main__":
    mcp.run()
