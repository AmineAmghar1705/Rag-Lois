"""Étape 7 : mesure la qualité de la recherche (sans le LLM)."""
from rag import rechercher

TESTS = [
    ("Suis-je responsable si je cause un dommage à quelqu'un ?", "1240"),
    ("À partir de quel âge peut-on se marier ?", "144"),
    ("Qu'est-ce que l'autorité parentale ?", "371-1"),
    ("Combien de temps ai-je pour agir en justice ?", "2224"),
    ("Un contrat signé est-il obligatoire ?", "1103"),
    ("Ai-je droit au respect de ma vie privée ?", "9"),
    ("Qu'est-ce que le droit de propriété ?", "544"),
]

K_VALEURS = [1, 3, 8]


def main():
    trouves = {k: 0 for k in K_VALEURS}

    for question, attendu in TESTS:
        nums = [a["num"] for a in rechercher(question, k=max(K_VALEURS))]
        rang = nums.index(attendu) + 1 if attendu in nums else None

        etat = f"rang {rang}" if rang else "absent"
        print(f"art. {attendu} : {etat}  ({question})")

        fork in K_VALEURS:
            if rang and rang <= k:
                trouves[k] += 1

    print()
    for k in K_VALEURS:
        print(f"Top-{k} : {trouves[k]}/{len(TESTS)} = {trouves[k] / len(TESTS):.0%}")


if __name__ == "__main__":
    main()