from sqlmodel import Session, text
from typing import List

def search_similar_chunks(session: Session, query_embedding: list[float], limit: int = 5) -> List[str]:

    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    query = text("""
        SELECT content
        FROM embeddings
        ORDER BY embedding <-> CAST(:embedding AS vector)
        LIMIT :limit
    """)

    result = session.exec(
        query,
        params={
            "embedding": embedding_str,
            "limit": limit
        }
    )

    rows = result.fetchall()

    return [row[0] for row in rows]