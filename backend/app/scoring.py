"""Calcul du score de risque (ISO 31000 / ISO 27005).

Score = probabilité (1-5) x impact (1-5)  -> de 1 à 25.
Exemple : probabilité 3 x impact 5 = 15 -> niveau "Élevé".
"""


def compute_score(probability: int, impact: int) -> int:
    if not (1 <= probability <= 5 and 1 <= impact <= 5):
        raise ValueError("probability et impact doivent être entre 1 et 5")
    return probability * impact


def risk_level(score: int) -> str:
    if score <= 4:
        return "Faible"
    if score <= 9:
        return "Moyen"
    if score <= 15:
        return "Élevé"
    return "Critique"
