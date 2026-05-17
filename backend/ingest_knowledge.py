#!/usr/bin/env python3
"""
Knowledge ingestion pipeline for the PM Mentor Agent.
Parses PDFs and text content, chunks them, generates embeddings,
and stores in Neon PostgreSQL with pgvector.

Usage:
    # Ingest a PDF book
    python ingest_knowledge.py pdf /path/to/book.pdf --source-name "Decode and Conquer"

    # Ingest a text/markdown file
    python ingest_knowledge.py text /path/to/article.md --source-name "Substack: Article Title"

    # Ingest all PDFs in a directory
    python ingest_knowledge.py dir /path/to/books/
"""

import argparse
import json
import os
import sys
from datetime import datetime

import fitz  # PyMuPDF
import psycopg2
import google.generativeai as genai

VECTOR_DB_URL = os.getenv('VECTOR_DB_URL', '')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072
CHUNK_SIZE = 800  # tokens approx (chars / 4)
CHUNK_OVERLAP = 200


def configure_genai():
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        print("Get one at https://aistudio.google.com/apikey")
        sys.exit(1)
    genai.configure(api_key=GEMINI_API_KEY)


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file, page by page."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            pages.append({
                'page_num': page_num + 1,
                'text': text.strip()
            })
    doc.close()
    return pages


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks by character count (approx token-based)."""
    char_chunk_size = chunk_size * 4
    char_overlap = overlap * 4

    chunks = []
    start = 0
    while start < len(text):
        end = start + char_chunk_size
        chunk = text[start:end]

        # Try to break at a sentence boundary
        if end < len(text):
            last_period = chunk.rfind('. ')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > char_chunk_size * 0.5:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        stripped = chunk.strip()
        if stripped:
            chunks.append(stripped)
        start = end - char_overlap

    return chunks


def generate_embeddings(texts, batch_size=50):
    """Generate embeddings for a list of texts using Google's embedding model."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=batch,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSIONS
        )
        all_embeddings.extend(result['embedding'])
        print(f"    Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks")
    return all_embeddings


def store_chunks(chunks_data):
    """Store chunks with embeddings in the database."""
    conn = psycopg2.connect(VECTOR_DB_URL)
    cursor = conn.cursor()

    for chunk in chunks_data:
        cursor.execute('''
            INSERT INTO knowledge_chunks (source_type, source_name, chunk_text, chunk_index, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            chunk['source_type'],
            chunk['source_name'],
            chunk['chunk_text'],
            chunk['chunk_index'],
            json.dumps(chunk.get('metadata', {})),
            str(chunk['embedding'])
        ))

    conn.commit()
    conn.close()


def check_already_ingested(source_name):
    """Check if a source has already been ingested."""
    conn = psycopg2.connect(VECTOR_DB_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM knowledge_chunks WHERE source_name = %s', (source_name,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def ingest_pdf(pdf_path, source_name=None):
    """Ingest a PDF file into the knowledge base."""
    if source_name is None:
        source_name = os.path.basename(pdf_path)

    if check_already_ingested(source_name):
        print(f"  Skipping '{source_name}' — already ingested")
        return 0

    print(f"  Extracting text from: {pdf_path}")
    pages = extract_text_from_pdf(pdf_path)
    print(f"  Extracted {len(pages)} pages")

    # Combine all page text and chunk it
    full_text = "\n\n".join(p['text'] for p in pages)
    chunks = chunk_text(full_text)
    print(f"  Created {len(chunks)} chunks")

    # Generate embeddings
    configure_genai()
    print("  Generating embeddings...")
    embeddings = generate_embeddings(chunks)

    # Prepare and store
    chunks_data = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunks_data.append({
            'source_type': 'book',
            'source_name': source_name,
            'chunk_text': chunk,
            'chunk_index': i,
            'metadata': {'total_pages': len(pages)},
            'embedding': embedding,
        })

    print("  Storing in database...")
    store_chunks(chunks_data)
    print(f"  Done! Stored {len(chunks_data)} chunks for '{source_name}'")
    return len(chunks_data)


def ingest_text(text_path, source_name=None, source_type='article'):
    """Ingest a text/markdown file into the knowledge base."""
    if source_name is None:
        source_name = os.path.basename(text_path)

    if check_already_ingested(source_name):
        print(f"  Skipping '{source_name}' — already ingested")
        return 0

    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"  Created {len(chunks)} chunks from '{source_name}'")

    configure_genai()
    print("  Generating embeddings...")
    embeddings = generate_embeddings(chunks)

    chunks_data = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunks_data.append({
            'source_type': source_type,
            'source_name': source_name,
            'chunk_text': chunk,
            'chunk_index': i,
            'metadata': {},
            'embedding': embedding,
        })

    print("  Storing in database...")
    store_chunks(chunks_data)
    print(f"  Done! Stored {len(chunks_data)} chunks for '{source_name}'")
    return len(chunks_data)


def ingest_text_content(text, source_name, source_type='article'):
    """Ingest raw text content (e.g., scraped article) into the knowledge base."""
    if check_already_ingested(source_name):
        print(f"  Skipping '{source_name}' — already ingested")
        return 0

    chunks = chunk_text(text)
    print(f"  Created {len(chunks)} chunks from '{source_name}'")

    configure_genai()
    print("  Generating embeddings...")
    embeddings = generate_embeddings(chunks)

    chunks_data = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunks_data.append({
            'source_type': source_type,
            'source_name': source_name,
            'chunk_text': chunk,
            'chunk_index': i,
            'metadata': {},
            'embedding': embedding,
        })

    print("  Storing in database...")
    store_chunks(chunks_data)
    print(f"  Done! Stored {len(chunks_data)} chunks for '{source_name}'")
    return len(chunks_data)


def ingest_directory(dir_path):
    """Ingest all PDFs in a directory."""
    total = 0
    for filename in sorted(os.listdir(dir_path)):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(dir_path, filename)
            total += ingest_pdf(pdf_path)
    return total


def main():
    parser = argparse.ArgumentParser(description='Ingest knowledge sources for PM Mentor Agent')
    parser.add_argument('mode', choices=['pdf', 'text', 'dir'], help='Ingestion mode')
    parser.add_argument('path', help='Path to file or directory')
    parser.add_argument('--source-name', help='Custom name for the source')
    args = parser.parse_args()

    print(f"[{datetime.now().isoformat()}] Starting ingestion...")

    if args.mode == 'pdf':
        ingest_pdf(args.path, args.source_name)
    elif args.mode == 'text':
        ingest_text(args.path, args.source_name)
    elif args.mode == 'dir':
        total = ingest_directory(args.path)
        print(f"\n  Total chunks ingested from directory: {total}")


if __name__ == '__main__':
    main()
