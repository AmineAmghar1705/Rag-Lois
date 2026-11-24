# Image de l'application pour Google Cloud Run (CPU, port donné par la variable PORT).
FROM python:3.12-slim

# utilisateur sans droits d'administration
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    GENERATION=mistral
WORKDIR /home/user/app

# torch en version CPU (pas de GPU sur Cloud Run), puis le reste
COPY --chown=user deploy/requirements.txt requirements.txt
RUN pip install --no-cache-dir --user torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --user -r requirements.txt

# Modèles téléchargés pendant la construction : le démarrage ne retélécharge rien
RUN python -c "from sentence_transformers import CrossEncoder, SentenceTransformer; \
SentenceTransformer('intfloat/multilingual-e5-base'); CrossEncoder('BAAI/bge-reranker-v2-m3')"

COPY --chown=user app.py rag.py ./
COPY --chown=user templates templates
COPY --chown=user chroma chroma

# Cloud Run indique le port dans $PORT (8080 par défaut).
# 1 processus (les modèles prennent ~4 Go), 4 fils pour servir plusieurs visiteurs.
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120 app:app
