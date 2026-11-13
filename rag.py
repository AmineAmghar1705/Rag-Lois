"""Étape 5 : cherche les articles les plus proches d'une question, puis répond."""
import chromadb
import ollama
from sentence_transformers import SentenceTransformer

MODELE = "intfloat/multilingual-e5-base"
LLM = "mistral"

CONSIGNES = """Tu es un assistant qui explique le droit français.
Réponds uniquement à partir des articles fournis.
Cite chaque article utilisé sous la forme (Code civil, art. 1240).
Si les articles ne suffisent pas pour répondre, dis-le clairement.
Précise que c'est une information générale, pas un conseil juridique."""

# chargés une seule fois, au démarrage
modele = SentenceTransformer(MODELE)
collection = chromadb.PersistentClient(path="chroma").get_collection("lois")


def rechercher(question, k=8):
    vecteur = modele.encode("query: " + question, normalize_embeddings=True)
    res = collection.query(query_embeddings=[vecteur.tolist()], n_results=k)

    articles = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        articles.append({
            "code": meta["code"],
            "num": meta["num"],
            "lien": meta["lien"],
            "texte": doc,
            "score": round(1 - dist, 3),
        })
    return articles


def repondre(question, k=8):
    articles = rechercher(question, k)
    contexte = "\n\n".join(f"[{a['code']}, art. {a['num']}]\n{a['texte']}" for a in articles)

    reponse = ollama.chat(
        model=LLM,
        messages=[
            {"role": "system", "content": CONSIGNES},
            {"role": "user", "content": f"Articles :\n{contexte}\n\nQuestion : {question}"},
        ],
    )
    return reponse["message"]["content"], articles


if __name__ == "__main__":
    question = input("Ta question : ")
    texte, articles = repondre(question)
    print("\n" + texte + "\n")
    print("Sources :")
    for a in articles:
        print(f"- {a['code']} art. {a['num']} ({a['score']}) {a['lien']}")