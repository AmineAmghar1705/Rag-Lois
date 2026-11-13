"""Étape 7 : mesure la qualité de la recherche (sans le LLM)."""
import json
from pathlib import Path

from rag import rechercher

with Path("tests.json").open(encoding="utf-8") as f:
    TESTS = [(t["question"], t["article"]) for t in json.load(f)]

K_VALEURS = [1, 3, 8]


def main():
    trouves = {k: 0 for k in K_VALEURS}

    for question, attendu in TESTS:
        nums = [a["num"] for a in rechercher(question, k=max(K_VALEURS))]
        rang = nums.index(attendu) + 1 if attendu in nums else None

        etat = f"rang {rang}" if rang else "absent"
        print(f"art. {attendu} : {etat}  ({question})")

        for k in K_VALEURS:
            if rang and rang <= k:
                trouves[k] += 1

    print()
    for k in K_VALEURS:
        print(f"Top-{k} : {trouves[k]}/{len(TESTS)} = {trouves[k] / len(TESTS):.0%}")


if __name__ == "__main__":
    main()