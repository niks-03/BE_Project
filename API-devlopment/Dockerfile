FROM python:latest

WORKDIR /app

COPY RAG_MODEL_DEV/requirements2.txt .

RUN pip install --no-cache-dir -r requirements2.txt

RUN python -c "import nltk; nltk.download('stopwords', quiet=True); nltk.download('punkt', quiet=True); nltk.download('wordnet', quiet=True); nltk.download('punkt_tab', quiet=True)"

COPY RAG_MODEL_DEV/ .

COPY RAG_MODEL_DEV/.env .

EXPOSE 8000

ENV FASTAPI_APP=app.py

CMD [ "fastapi", "run", "app.py" ]