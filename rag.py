"""Étape 5 : cherche les articles les plus proches d'une question, puis répond."""
import chromadb
import ollama
import torch
from sentence_transformers import CrossEncoder, SentenceTransformer

MODELE = "intfloat/multilingual-e5-base"
LLM = "mistral"

# Reclassement : la recherche vectorielle propose CANDIDATS articles, puis un
# cross-encoder relit chaque couple (question, article) et les reclasse.
# Il comble en partie l'écart de vocabulaire entre la question et le texte de loi
# (« union libre » / concubinage, « location » / louage...).
# Sur les 47 tests : Top-1 23 -> 26, Top-3 32 -> 35, Top-8 35 -> 38.
# 20 candidats donnent le même résultat que 50, pour ~1,2 s par question sur puce Apple.
RECLASSEMENT = True
RECLASSEUR = "BAAI/bge-reranker-v2-m3"
CANDIDATS = 20

CONSIGNES = """Tu es un assistant qui explique le droit français.
Réponds uniquement à partir des articles fournis.
Cite chaque article utilisé sous la forme (Code civil, art. 1240).
Si les articles ne suffisent pas pour répondre, dis-le clairement.
Précise que c'est une information générale, pas un conseil juridique."""

# chargés une seule fois, au démarrage
modele = SentenceTransformer(MODELE)
collection = chromadb.PersistentClient(path="chroma").get_collection("lois")
reclasseur = None
if RECLASSEMENT:
    appareil = "mps" if torch.backends.mps.is_available() else "cpu"
    reclasseur = CrossEncoder(RECLASSEUR, max_length=512, device=appareil)


def rechercher(question, k=8):
    vecteur = modele.encode("query: " + question, normalize_embeddings=True)
    n = max(k, CANDIDATS) if reclasseur else k
    res = collection.query(query_embeddings=[vecteur.tolist()], n_results=n)

    articles = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        articles.append({
            "code": meta["code"],
            "num": meta["num"],
            "lien": meta["lien"],
            "texte": doc,
            "score": round(1 - dist, 3),
        })

    if reclasseur:
        scores = reclasseur.predict([(question, a["texte"]) for a in articles], batch_size=32)
        for a, s in zip(articles, scores):
            a["score"] = round(float(s), 3)  # pertinence selon le reclasseur, entre 0 et 1
        articles.sort(key=lambda a: a["score"], reverse=True)
    return articles[:k]


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