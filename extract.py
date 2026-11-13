"""Étape 3 : extrait les articles en vigueur des fichiers XML LEGI."""
import json
from pathlib import Path

from lxml import etree

RAW = Path("data/raw")
OUT = Path("data/articles.jsonl")
CODES = {"Code civil"}  # mettre set() pour garder tous les codes
MAX_CHARS = 6000        # coupe les très longs articles


def lire_article(fichier):
    root = etree.parse(str(fichier)).getroot()

    def champ(chemin):
        return (root.findtext(chemin) or "").strip()

    contenu = root.find(".//BLOC_TEXTUEL/CONTENU")
    texte = " ".join("".join(contenu.itertext()).split()) if contenu is not None else ""
    art_id = champ(".//META_COMMUN/ID")
    return {
        "id": art_id,
        "code": champ(".//CONTEXTE/TEXTE/TITRE_TXT"),
        "num": champ(".//META_ARTICLE/NUM"),
        "etat": champ(".//META_ARTICLE/ETAT"),
        "date_debut": champ(".//META_ARTICLE/DATE_DEBUT"),
        "texte": texte[:MAX_CHARS],
        "lien": f"https://www.legifrance.gouv.fr/codes/article_lc/{art_id}",
    }


def main():
    gardes = vus = 0
    with OUT.open("w", encoding="utf-8") as out:
        for fichier in RAW.rglob("LEGIARTI*.xml"):
            vus += 1
            try:
                art = lire_article(fichier)
            except etree.XMLSyntaxError:
                continue
            if art["etat"] != "VIGUEUR" or not art["texte"]:
                continue
            if CODES and art["code"] not in CODES:
                continue
            out.write(json.dumps(art, ensure_ascii=False) + "\n")
            gardes += 1
            if gardes % 1000 == 0:
                print(f"{gardes} articles gardés / {vus} lus")
    print(f"Terminé : {gardes} articles écrits dans {OUT}")


if __name__ == "__main__":
    main()