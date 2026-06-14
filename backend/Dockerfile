FROM python:3.11-slim

# Install libmagic (needed for python-magic on Linux)
RUN apt-get update && apt-get install -y libmagic1 tesseract-ocr && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install python-magic instead of python-magic-bin (Linux compatible)
RUN pip install --no-cache-dir $(grep -v "python-magic-bin" requirements.txt | tr '\n' ' ') python-magic

COPY . .

RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
