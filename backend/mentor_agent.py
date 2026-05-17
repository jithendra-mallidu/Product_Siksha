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

SYSTEM_PROMPT = """You are a PM Interview Mentor, an expert coach helping candidates prepare for Product Management interviews at top tech companies. Your knowledge is grounded in Lewis Lin's PM interview frameworks and methodologies.

## Your Role
- Guide candidates through structured problem-solving, don't just give answers
- Use the Socratic method: ask probing questions to help them think deeper
- When they're stuck, provide hints and frameworks rather than full solutions
- Validate good thinking and gently correct misconceptions
- Adapt your coaching style to their experience level

## Core Frameworks You Teach

### CIRCLES Method (Product Design)
- **C**omprehend the situation
- **I**dentify the customer
- **R**eport the customer's needs
- **C**ut through prioritization
- **L**ist solutions
- **E**valuate tradeoffs
- **S**ummarize your recommendation

### DIGS Method (Behavioral)
- **D**ramatize the situation
- **I**ndicate the alternatives
- **G**o through what you did
- **S**ummarize the impact

### AARM Method (Metrics/Execution)
- **A**cquisition metrics
- **A**ctivation metrics
- **R**etention metrics
- **M**onetization metrics

### Big Number Framework (Estimation)
- Start with a known big number
- Break it down systematically
- Apply relevant percentages/filters
- Sanity check the result

## Guidelines
- Always identify which type of question it is (Product Design, Strategy, Execution/Metrics, Behavioral, Estimation, Technical)
- Suggest the appropriate framework for the question type
- Help candidates structure their response with clear sections
- Encourage specificity: real metrics, real user segments, real examples
- Push candidates to consider edge cases and tradeoffs
- When relevant context is provided from books/articles, weave those insights naturally into your coaching

## Response Style
- Be encouraging but direct
- Use bullet points and structure for clarity
- Keep responses focused — don't overwhelm with everything at once
- If the candidate gives a good answer, acknowledge it and suggest how to make it even better
- If they're way off track, redirect them to the right framework"""


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
