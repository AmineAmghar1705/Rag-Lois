"""Étape 4 : transforme les articles en vecteurs et les range dans ChromaDB."""
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

ARTICLES = Path("data/articles.jsonl")
MODELE = "intfloat/multilingual-e5-base"
LOT = 128  # nombre d'articles traités à la fois

def main():
    with ARTICLES.open(encoding="utf-8") as f:
        articles = [json.loads(ligne) for ligne in f]
    # enlève les doublons éventuels (même identifiant)
    articles = list({a["id"]: a for a in articles}.values())
    print(f"{len(articles)} articles à indexer")

    modele = SentenceTransformer(MODELE)
    client = chromadb.PersistentClient(path="chroma")
    collection = client.get_or_create_collection(
        "lois", metadata={"hnsw:space": "cosine"}
    )

    for i in range(0, len(articles), LOT):
        lot = articles[i:i + LOT]
        textes = [f"{a['code']}, article {a['num']} : {a['texte']}" for a in lot]
        vecteurs = modele.encode(
            ["passage: " + t for t in textes], normalize_embeddings=True
        )
        collection.upsert(
            ids=[a["id"] for a in lot],
            embeddings=vecteurs.tolist(),
            documents=textes,
            metadatas=[{"code": a["code"], "num": a["num"], "lien": a["lien"]} for a in lot],
        )
        print(f"{i + len(lot)} / {len(articles)} indexés")

    print("Index prêt dans le dossier chroma/")

if __name__ == "__main__":
    main()