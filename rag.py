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

# Reformulation : avant la recherche, Mistral réécrit la question en termes juridiques
# (« prêter sa voiture » -> « prêt à usage »). On cherche avec la question ET la
# reformulation, puis le reclasseur trie l'ensemble des candidats.
# Testé et désactivé : sur les 47 tests, au mieux ±1 question (Top-1 26 -> 27,
# Top-3 35 -> 36, Top-8 38 -> 38) pour ~0,9 s de plus par question. Mistral 7B
# manque de vocabulaire juridique : il paraphrase ou se trompe de notion.
# À retenter avec un modèle plus fort.
REFORMULATION = False

CONSIGNES_REFORMULATION = """Tu réécris des questions de particuliers dans le vocabulaire du Code civil français.
Ne réponds pas à la question. Donne une seule phrase courte qui nomme la notion juridique
précise (nom du contrat, de l'institution, du délai, de l'action) dans les termes de la loi.

Exemples :
Question : Mon chien a mordu le facteur, qui paie ?
Reformulation : Responsabilité du propriétaire d'un animal pour le dommage causé par cet animal.
Question : Le mur entre mon jardin et celui du voisin appartient à qui ?
Reformulation : Présomption de mitoyenneté du mur servant de séparation entre deux héritages."""

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


def reformuler(question):
    """Demande à Mistral la question dans le vocabulaire du Code civil."""
    reponse = ollama.chat(
        model=LLM,
        messages=[
            {"role": "system", "content": CONSIGNES_REFORMULATION},
            {"role": "user", "content": f"Question : {question}\nReformulation :"},
        ],
        options={"temperature": 0},  # même question -> même reformulation
    )
    return reponse["message"]["content"].strip().split("\n")[0]


def chercher_vecteurs(requetes, n):
    """Recherche vectorielle pour chaque requête, candidats fusionnés sans doublon."""
    vecteurs = modele.encode(["query: " + r for r in requetes], normalize_embeddings=True)
    res = collection.query(query_embeddings=vecteurs.tolist(), n_results=n)

    articles, vus = [], set()
    for i in range(len(requetes)):
        for doc, meta, dist in zip(res["documents"][i], res["metadatas"][i], res["distances"][i]):
            if meta["num"] in vus:
                continue
            vus.add(meta["num"])
            articles.append({
                "code": meta["code"],
                "num": meta["num"],
                "lien": meta["lien"],
                "texte": doc,
                "score": round(1 - dist, 3),
            })
    return articles


def rechercher(question, k=8, reformulation=None):
    """reformulation : texte déjà calculé (évite de rappeler Mistral), sinon calculée ici."""
    requetes = [question]
    if REFORMULATION:
        requetes.append(reformulation or reformuler(question))

    n = max(k, CANDIDATS) if reclasseur else k
    articles = chercher_vecteurs(requetes, n)

    if reclasseur:
        requete_reclassement = " ".join(requetes)
        scores = reclasseur.predict([(requete_reclassement, a["texte"]) for a in articles], batch_size=32)
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