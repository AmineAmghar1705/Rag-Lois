"""Étape 3 : extrait les articles en vigueur des fichiers XML LEGI."""
import json
from pathlib import Path

from lxml import etree

RAW = Path("data/raw")
OUT = Path("data/articles.jsonl")
CODES = {"Code civil"}  # mettre set() pour garder tous les codes
MAX_CHARS = 6000        # coupe les très longs articles


def lire_titres(root):
    """Titres des parties du code qui contiennent l'article (Livre > Titre > Chapitre > Section).

    Ils apportent le vocabulaire juridique absent du texte de l'article
    (ex. art. 1875 : « Titre X : Du prêt > Chapitre Ier : Du prêt à usage »).
    Un niveau peut avoir plusieurs versions datées : on garde celle en vigueur.
    """
    titres = []
    tm = root.find(".//CONTEXTE/TEXTE/TM")
    while tm is not None:
        versions = tm.findall("TITRE_TM")
        if versions:
            actuelles = [v for v in versions if v.get("fin") == "2999-01-01"] or versions
            titre = max(actuelles, key=lambda v: v.get("debut") or "")
            titres.append(" ".join((titre.text or "").split()))
        tm = tm.find("TM")
    return titres


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
        "titres": lire_titres(root),
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