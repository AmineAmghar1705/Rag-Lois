"""Étape 6 : petite application web pour poser des questions."""
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, render_template, request

from rag import repondre

app = Flask(__name__)

# En ligne, chaque question coûte un appel à l'API Mistral : on limite le nombre
# de questions par adresse IP (en mémoire, suffisant pour un seul processus).
LIMITE_QUESTIONS = 10
FENETRE_SECONDES = 60
historique = defaultdict(deque)


def trop_de_questions():
    # derrière un tunnel Cloudflare, la vraie IP est dans CF-Connecting-IP ;
    # derrière le proxy de Cloud Run, dans X-Forwarded-For
    ip = (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For")
        or request.remote_addr
        or ""
    ).split(",")[0].strip()
    maintenant = time.monotonic()
    appels = historique[ip]
    while appels and maintenant - appels[0] > FENETRE_SECONDES:
        appels.popleft()
    if len(appels) >= LIMITE_QUESTIONS:
        return True
    appels.append(maintenant)
    return False


@app.get("/")
def accueil():
    return render_template("dtyle.html")


@app.post("/api/question")
def question():
    donnees = request.get_json(silent=True) or {}
    texte = (donnees.get("question") or "").strip()

    if not texte:
        return jsonify({"erreur": "Pose une question."}), 400
    if len(texte) > 2000:
        return jsonify({"erreur": "Question trop longue (2000 caractères max)."}), 400
    if trop_de_questions():
        return jsonify({"erreur": "Trop de questions d'affilée, réessaie dans une minute."}), 429

    try:
        reponse, articles = repondre(texte)
    except Exception:
        app.logger.exception("Échec de la génération")
        return jsonify({"erreur": "Le service de génération ne répond pas, réessaie plus tard."}), 503
    return jsonify({"reponse": reponse, "sources": articles})


if __name__ == "__main__":
    app.run(port=5001)
