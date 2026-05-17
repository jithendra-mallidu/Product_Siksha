"""
PM Mentor Agent - RAG-powered interview coaching using Claude API.
Retrieves relevant knowledge from Lewis Lin's books/articles and provides
structured mentoring guidance for PM interview questions.
"""

import json
import os

import psycopg2
from anthropic import Anthropic
import google.generativeai as genai

VECTOR_DB_URL = os.getenv('VECTOR_DB_URL', '')

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
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


def get_query_embedding(query):
    """Generate embedding for a search query."""
    if not GEMINI_API_KEY:
        return None
    genai.configure(api_key=GEMINI_API_KEY)
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=query,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=EMBEDDING_DIMENSIONS
    )
    return result['embedding']


def retrieve_relevant_chunks(query, top_k=5):
    """Retrieve the most relevant knowledge chunks for a query using vector similarity."""
    if not GEMINI_API_KEY:
        return []

    embedding = get_query_embedding(query)
    if not embedding:
        return []

    conn = psycopg2.connect(VECTOR_DB_URL)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT source_name, chunk_text, 1 - (embedding <=> %s::vector) as similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    ''', (str(embedding), str(embedding), top_k))

    results = []
    for row in cursor.fetchall():
        results.append({
            'source': row[0],
            'text': row[1],
            'similarity': float(row[2])
        })

    conn.close()
    return results


def build_context_message(question_text, question_category, company, chunks):
    """Build the context message with retrieved knowledge."""
    context_parts = []

    if chunks:
        context_parts.append("## Relevant Knowledge Base Context")
        for chunk in chunks:
            if chunk['similarity'] > 0.3:
                context_parts.append(f"\n**From: {chunk['source']}**\n{chunk['text']}")

    context_parts.append(f"\n## Current Question")
    context_parts.append(f"**Category:** {question_category}")
    context_parts.append(f"**Company:** {company}")
    context_parts.append(f"**Question:** {question_text}")

    return "\n".join(context_parts)


def chat_with_mentor(question_text, question_category, company, conversation_history, user_message):
    """
    Main mentor chat function.
    Takes the question context, conversation history, and new user message.
    Returns the mentor's response.
    """
    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY not configured. Please set it in your environment variables."

    # Retrieve relevant knowledge for the question + user's message
    search_query = f"{question_category} {question_text} {user_message}"
    chunks = retrieve_relevant_chunks(search_query)

    # Build the context
    context = build_context_message(question_text, question_category, company, chunks)

    # Build messages for Claude
    messages = []

    # Add context as the first user message if this is a new conversation
    if not conversation_history:
        messages.append({
            "role": "user",
            "content": f"{context}\n\n---\n\nThe candidate says: {user_message}"
        })
    else:
        # Include context in the first message of history
        messages.append({
            "role": "user",
            "content": f"{context}\n\n---\n\nThe candidate says: {conversation_history[0]['content']}"
        })
        # Add the rest of the conversation
        for msg in conversation_history[1:]:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        # Add the new user message
        messages.append({
            "role": "user",
            "content": user_message
        })

    # Call Claude API
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    return response.content[0].text
