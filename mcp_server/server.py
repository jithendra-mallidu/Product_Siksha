#!/usr/bin/env python3
"""
PM Mentor MCP Server - Knowledge retrieval for PM interview coaching.

Exposes the PM interview knowledge base (Lewis Lin's books + Substack articles)
as MCP tools and prompts. The server handles RAG retrieval (free Gemini embeddings
+ pgvector search) and returns relevant context. The host LLM (Claude, ChatGPT,
Gemini, etc.) does the reasoning — so the token cost is on the client, not us.
"""

import os
from pathlib import Path

import psycopg2
import google.generativeai as genai
from mcp.server.fastmcp import FastMCP

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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072

MENTOR_SYSTEM_PROMPT = """You are a PM Interview Mentor, an expert coach helping candidates prepare for Product Management interviews at top tech companies.

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

def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="PM Mentor MCP Server")
    parser.add_argument("--http", action="store_true", help="Run as HTTP server (default: stdio)")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    return parser.parse_args()

_args = _parse_args() if __name__ == "__main__" else None

mcp = FastMCP(
    "pm-mentor",
    instructions=(
        "PM Interview Knowledge Base — retrieves relevant coaching context from "
        "Lewis Lin's PM interview books and Substack articles. Use the retrieve tool "
        "to get context, then coach the user using that context with the pm_coach prompt."
    ),
    host=_args.host if _args else "127.0.0.1",
    port=_args.port if _args else 8080,
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


# --- MCP Tools ---


@mcp.tool()
def pm_retrieve(
    query: str,
    question: str = "",
    category: str = "",
    company: str = "",
    top_k: int = 5,
) -> str:
    """Retrieve relevant PM interview knowledge from the vector database.
    Returns context from Lewis Lin's books and Substack articles that is most
    relevant to the query. Use this before coaching a candidate on a PM question.

    Args:
        query: The search query — can be a question, topic, or the candidate's answer
        question: The specific PM interview question being practiced
        category: Question category (Product Design, Strategy, Execution/Metrics, Behavioral, Estimation, Technical)
        company: Target company (Google, Meta, Amazon, etc.)
        top_k: Number of knowledge chunks to retrieve (default 5, max 10)
    """
    top_k = min(top_k, 10)
    search_query = " ".join(filter(None, [category, question, query]))
    chunks = retrieve_relevant_chunks(search_query, top_k)

    if not chunks:
        return "No relevant content found. The knowledge base may be unavailable."

    parts = []
    parts.append(f"## Retrieved Knowledge Context")
    if question:
        parts.append(f"**Question:** {question}")
    if category:
        parts.append(f"**Category:** {category}")
    if company:
        parts.append(f"**Company:** {company}")
    parts.append("")

    for i, chunk in enumerate(chunks, 1):
        if chunk["similarity"] > 0.2:
            parts.append(
                f"### Source {i}: {chunk['source']} "
                f"(relevance: {chunk['similarity']:.0%})\n{chunk['text']}\n"
            )

    parts.append(
        "\n---\n*Use this context to inform your coaching. "
        "Draw on specific insights rather than giving generic advice.*"
    )
    return "\n".join(parts)


@mcp.tool()
def pm_knowledge_stats() -> str:
    """Get statistics about the PM interview knowledge base — total chunks, sources, and coverage."""
    if not VECTOR_DB_URL:
        return "Knowledge base unavailable: VECTOR_DB_URL not configured."

    conn = psycopg2.connect(VECTOR_DB_URL)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM knowledge_chunks")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT source_type, COUNT(*), COUNT(DISTINCT source_name) "
        "FROM knowledge_chunks GROUP BY source_type"
    )
    by_type = cursor.fetchall()

    cursor.execute(
        "SELECT source_name, COUNT(*) FROM knowledge_chunks "
        "GROUP BY source_name ORDER BY COUNT(*) DESC LIMIT 10"
    )
    top_sources = cursor.fetchall()

    conn.close()

    lines = [f"## PM Knowledge Base Stats", f"**Total chunks:** {total}\n"]
    for stype, count, distinct in by_type:
        lines.append(f"- **{stype}**: {count} chunks from {distinct} sources")
    lines.append(f"\n### Top Sources")
    for name, count in top_sources:
        lines.append(f"- {name}: {count} chunks")

    return "\n".join(lines)


# --- MCP Prompts ---


@mcp.prompt()
def pm_coach(question: str, category: str = "General", company: str = "Unknown") -> str:
    """Start a PM interview coaching session. Retrieves relevant knowledge and sets up
    the mentor persona so the host LLM can coach the candidate.

    Args:
        question: The PM interview question to practice
        category: Question category (Product Design, Strategy, Metrics, Behavioral, Estimation, Technical)
        company: Target company
    """
    chunks = retrieve_relevant_chunks(f"{category} {question}", top_k=5)

    context_parts = []
    if chunks:
        context_parts.append("## Relevant Knowledge Base Context\n")
        for chunk in chunks:
            if chunk["similarity"] > 0.2:
                context_parts.append(
                    f"**From: {chunk['source']}**\n{chunk['text']}\n"
                )
    context = "\n".join(context_parts)

    return (
        f"{MENTOR_SYSTEM_PROMPT}\n\n"
        f"---\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"## Current Session\n"
        f"**Question:** {question}\n"
        f"**Category:** {category}\n"
        f"**Company:** {company}\n\n"
        f"The candidate is ready to practice. Introduce the question, assess their "
        f"initial understanding, and guide them through a structured approach using "
        f"the retrieved context above. Start by asking what their initial thoughts are."
    )


@mcp.prompt()
def pm_mock_interview(category: str = "Product Design", company: str = "Google") -> str:
    """Start a full mock PM interview. The host LLM acts as interviewer, using the
    knowledge base to evaluate answers and provide realistic follow-up questions.

    Args:
        category: Interview category (Product Design, Strategy, Metrics, Behavioral, Estimation)
        company: Company to simulate the interview for
    """
    chunks = retrieve_relevant_chunks(
        f"{company} {category} interview question", top_k=3
    )

    example_questions = []
    for chunk in chunks:
        if chunk["similarity"] > 0.3:
            example_questions.append(chunk["text"][:200])

    return (
        f"You are a PM interviewer at {company} conducting a {category} interview.\n\n"
        f"## Your Role\n"
        f"- Ask one question at a time\n"
        f"- Listen to the candidate's answer before responding\n"
        f"- Ask realistic follow-up questions that probe deeper\n"
        f"- After 3-4 exchanges on a question, provide brief feedback and move to the next\n"
        f"- At the end, give an overall assessment with strengths and areas to improve\n\n"
        f"## Knowledge Context\n"
        f"{''.join(example_questions)}\n\n"
        f"Start by introducing yourself and asking the first {category} question. "
        f"Make it realistic for a {company} interview."
    )


if __name__ == "__main__":
    if _args and _args.http:
        print(f"Starting PM Mentor MCP server on http://{_args.host}:{_args.port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
