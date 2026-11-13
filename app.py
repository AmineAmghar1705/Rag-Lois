"""Étape 6 : petite application web pour poser des questions."""
from flask import Flask, jsonify, render_template, request

from rag import repondre

app = Flask(__name__)


@app.get("/")
def accueil():
    return render_template("index.html")


@app.post("/api/question")
def question():
    donnees = request.get_json(silent=True) or {}
    texte = (donnees.get("question") or "").strip()

    if not texte:
        return jsonify({"erreur": "Pose une question."}), 400
    if len(texte) > 2000:
        return jsonify({"erreur": "Question trop longue (2000 caractères max)."}), 400

    reponse, articles = repondre(texte)
    return jsonify({"reponse": reponse, "sources": articles})


if __name__ == "__main__":
    app.run(port=5001)