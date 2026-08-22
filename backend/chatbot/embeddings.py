import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# OpenAI allows up to 2048 inputs per call, but batching at 100 keeps
# individual requests well within rate-limit and token-count bounds.
_BATCH_SIZE = 100


def create_embedding(texts: list[str]):
    if not texts:
        return None

    try:
        all_embeddings = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            res = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            all_embeddings.extend(item.embedding for item in res.data)
        return all_embeddings

    except Exception as e:
        print(f"Embedding error: {str(e)}")
        return None
