import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_embedding(texts: list[str]):
    if not texts:
        return None

    try:
        res = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts   # 👈 list of strings
        )

        # ✅ return list of embeddings
        return [item.embedding for item in res.data]

    except Exception as e:
        print(f"Embedding error: {str(e)}")
        return None