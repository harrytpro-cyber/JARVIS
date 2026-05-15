"""
Résultats sportifs — TheSportsDB (gratuit, sans clé API).
Football : résultats, prochains matchs, classements (Ligue 1, Premier League, Liga…).
Recherche web générale via SerpAPI (optionnel, nécessite SERPAPI_KEY dans .env).
"""
import os
import requests

THESPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
SERPAPI_KEY      = os.getenv("SERPAPI_KEY", "")

_LIGUE_IDS = {
    "ligue 1":          "4334",
    "ligue1":           "4334",
    "premier league":   "4328",
    "liga":             "4335",
    "bundesliga":       "4331",
    "serie a":          "4332",
    "champions league": "4480",
    "ligue des champions": "4480",
    "ucl":              "4480",
}


def _cle_valide(key: str) -> bool:
    return bool(key and key.strip() and key not in ("", "VOTRE_CLE_ICI"))


def get_resultats_football(equipe: str = None, ligue: str = None) -> str:
    """Résultats et prochain match d'une équipe, ou derniers résultats d'une ligue."""
    try:
        if equipe:
            print(f"[SPORT] Recherche équipe : {equipe}")
            r    = requests.get(f"{THESPORTSDB_BASE}/searchteams.php", params={"t": equipe}, timeout=5)
            data = r.json()
            teams = data.get("teams")
            if not teams:
                return f"Je n'ai pas trouvé l'équipe {equipe}."

            team_id   = teams[0]["idTeam"]
            team_name = teams[0]["strTeam"]

            res_last = requests.get(f"{THESPORTSDB_BASE}/eventslast.php", params={"id": team_id}, timeout=5).json()
            res_next = requests.get(f"{THESPORTSDB_BASE}/eventsnext.php", params={"id": team_id}, timeout=5).json()

            matchs_passes = res_last.get("results", [])
            matchs_futurs = res_next.get("events", [])

            reponse = f"Concernant {team_name} : "
            if matchs_futurs:
                m = matchs_futurs[0]
                reponse += (
                    f"prochain match le {m.get('dateEvent', '?')} "
                    f"à {m.get('strTime', '?')} contre {m.get('strOpponent', '?')}. "
                )
            if matchs_passes:
                m = matchs_passes[0]
                reponse += (
                    f"Dernier résultat : {m.get('intHomeScore', '?')} - "
                    f"{m.get('intAwayScore', '?')} contre {m.get('strOpponent', '?')}."
                )
            if not matchs_futurs and not matchs_passes:
                return f"Aucune information récente pour {team_name}."
            return reponse

        else:
            nom_ligue = (ligue or "Ligue 1").lower()
            ligue_id  = _LIGUE_IDS.get(nom_ligue, "4334")
            r    = requests.get(f"{THESPORTSDB_BASE}/eventspastleague.php", params={"id": ligue_id}, timeout=5)
            data = r.json()
            matchs = data.get("events", [])
            if not matchs:
                return f"Aucun résultat trouvé pour {ligue or 'Ligue 1'}."
            lignes = []
            for m in matchs[-6:]:
                home = m.get("strHomeTeam", "?")
                away = m.get("strAwayTeam", "?")
                sh   = m.get("intHomeScore", "?")
                sa   = m.get("intAwayScore", "?")
                date = m.get("dateEvent", "?")
                lignes.append(f"{home} {sh}-{sa} {away} ({date})")
            return f"Derniers résultats {ligue or 'Ligue 1'} : " + " | ".join(lignes)

    except Exception as e:
        print(f"[SPORT] Erreur football : {e}")
        return "Impossible de récupérer les résultats football."


def get_classement_football(ligue: str = None) -> str:
    """Classement du Top 10 d'une ligue."""
    try:
        nom_ligue = (ligue or "Ligue 1").lower()
        ligue_id  = _LIGUE_IDS.get(nom_ligue, "4334")
        r    = requests.get(
            f"{THESPORTSDB_BASE}/lookuptable.php",
            params={"l": ligue_id, "s": "2024-2025"},
            timeout=8,
        )
        data    = r.json()
        tableau = data.get("table", [])
        if not tableau:
            return f"Classement {ligue or 'Ligue 1'} non disponible pour le moment."
        lignes = []
        for eq in tableau[:10]:
            pos   = eq.get("intRank", "?")
            nom   = eq.get("strTeam", "?")
            pts   = eq.get("intPoints", "?")
            joues = eq.get("intPlayed", "?")
            lignes.append(f"{pos}. {nom} {pts}pts ({joues}J)")
        return f"Classement {ligue or 'Ligue 1'} : " + " | ".join(lignes)
    except Exception as e:
        print(f"[SPORT] Erreur classement : {e}")
        return "Impossible de récupérer le classement."


def recherche_web(query: str) -> str | None:
    """Recherche Google via SerpAPI (nécessite SERPAPI_KEY dans .env)."""
    if not _cle_valide(SERPAPI_KEY):
        return None
    try:
        params = {"engine": "google", "q": query, "api_key": SERPAPI_KEY, "hl": "fr", "gl": "fr"}
        r      = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
        data   = r.json()
        if "news_results" in data:
            news    = data["news_results"][:3]
            reponse = f"Actualités pour {query} : "
            for n in news:
                reponse += f"- {n.get('title', '')} (via {n.get('source', '?')}) "
            return reponse.strip()
        if "organic_results" in data:
            results = data["organic_results"][:3]
            reponse = f"Résultats web pour {query} : "
            for res in results:
                snippet = res.get("snippet", "")
                reponse += f"- {res.get('title', '')} : {snippet} "
            return reponse.strip()
        return None
    except Exception as e:
        print(f"[WEB] Erreur SerpAPI : {e}")
        return None


def traiter_commande_sport(text: str) -> str | None:
    """Parse une commande vocale sport et retourne la réponse."""
    t = text.lower()

    # Classement
    if any(w in t for w in ["classement", "tableau", "palmarès"]):
        for ligue in _LIGUE_IDS:
            if ligue in t:
                return get_classement_football(ligue)
        return get_classement_football()  # Ligue 1 par défaut

    # Résultats d'une équipe spécifique
    # Extrait le nom d'équipe en supprimant les mots déclencheurs
    import re
    query = re.sub(
        r"\b(résultat|résultats|score|match|matchs|prochain|dernier|foot|football|"
        r"de|du|le|la|les|l'|équipe|joue|joué|contre|gagné|perdu)\b",
        "", t
    ).strip()
    query = re.sub(r"\s+", " ", query).strip()

    if query:
        return get_resultats_football(equipe=query)

    # Ligue par défaut
    for ligue in _LIGUE_IDS:
        if ligue in t:
            return get_resultats_football(ligue=ligue)

    return get_resultats_football()
