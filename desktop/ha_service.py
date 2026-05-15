"""
Intégration Home Assistant + Météo (Open-Meteo, gratuit).
Configuration via .env (HA_URL, HA_TOKEN) et jarvis_config.json (entités custom).

Pour configurer vos entités HA, ajoutez dans desktop/jarvis_config.json :
{
  "ha_custom_entities": {
    "lumieres": [{"nom": "salon", "entity_id": "light.salon"}],
    "prises":   [{"nom": "bureau", "entity_id": "switch.prise_bureau"}],
    "capteurs": [{"nom": "salon", "entity_id": "sensor.salon_temperature"}]
  }
}
"""
import os
import json
import requests
from datetime import datetime

# ── Connexion Home Assistant ──────────────────────────────────────────
HA_URL    = os.getenv("HA_URL", "").rstrip("/")
HA_TOKEN  = os.getenv("HA_TOKEN", "")
HA_HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type":  "application/json",
}

# ── Météo — ville par défaut (surchargeable via jarvis_config.json) ───
VILLE_PAR_DEFAUT = "Paris"
LAT_PAR_DEFAUT   = 48.8566
LON_PAR_DEFAUT   = 2.3522

# ── Entités Home Assistant (vides par défaut, remplies par jarvis_config.json) ──
PIECES_LUMIERES: dict[str, str] = {}
PIECES_PRISES:   dict[str, str] = {}
PIECES_CAPTEURS: dict[str, str] = {}

# ── Couleurs RGB ──────────────────────────────────────────────────────
COULEURS_MAP: dict[str, list[int]] = {
    "rouge":     [255, 0,   0  ],
    "bleu":      [0,   0,   255],
    "vert":      [0,   255, 0  ],
    "blanc":     [255, 255, 255],
    "orange":    [255, 140, 0  ],
    "violet":    [148, 0,   211],
    "rose":      [255, 20,  147],
    "jaune":     [255, 255, 0  ],
    "cyan":      [0,   255, 255],
    "magenta":   [255, 0,   255],
    "turquoise": [64,  224, 208],
    "or":        [255, 215, 0  ],
    "argent":    [192, 192, 192],
    "indigo":    [75,  0,   130],
    "marron":    [139, 69,  19 ],
    "corail":    [255, 127, 80 ],
    "lavande":   [230, 230, 250],
}

# ── Codes météo Open-Meteo ────────────────────────────────────────────
CODES_METEO: dict[int, str] = {
    0:  "ciel dégagé",
    1:  "principalement clair", 2: "partiellement nuageux", 3: "couvert",
    45: "brouillard", 48: "brouillard givrant",
    51: "bruine légère", 53: "bruine modérée", 55: "bruine dense",
    61: "pluie faible", 63: "pluie modérée", 65: "pluie forte",
    71: "neige faible", 73: "neige modérée", 75: "neige forte",
    80: "averses faibles", 81: "averses modérées", 82: "averses violentes",
    85: "averses de neige", 86: "averses de neige fortes",
    95: "orage", 96: "orage avec grêle", 99: "orage violent avec grêle",
}

_HA_CUSTOM_KEYS: dict = {"lumieres": set(), "prises": set(), "capteurs": set()}


# ── Chargement de la config ────────────────────────────────────────────

def _charger_config():
    """Charge jarvis_config.json et met à jour ville, entités HA."""
    global VILLE_PAR_DEFAUT, LAT_PAR_DEFAUT, LON_PAR_DEFAUT, _HA_CUSTOM_KEYS
    global HA_URL, HA_TOKEN

    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
        if not os.path.exists(p):
            return
        with open(p, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        if "ville" in cfg:
            VILLE_PAR_DEFAUT = cfg["ville"]
        if "ha_url" in cfg:
            HA_URL = cfg["ha_url"].rstrip("/")
        if "ha_token" in cfg:
            HA_TOKEN = cfg["ha_token"]
            HA_HEADERS["Authorization"] = f"Bearer {HA_TOKEN}"

        # Nettoyer les entités custom précédentes
        for k in _HA_CUSTOM_KEYS["lumieres"]:
            PIECES_LUMIERES.pop(k, None)
        for k in _HA_CUSTOM_KEYS["prises"]:
            PIECES_PRISES.pop(k, None)
        for k in _HA_CUSTOM_KEYS["capteurs"]:
            PIECES_CAPTEURS.pop(k, None)
        _HA_CUSTOM_KEYS = {"lumieres": set(), "prises": set(), "capteurs": set()}

        custom = cfg.get("ha_custom_entities", {})
        for entry in custom.get("lumieres", []):
            nom = entry["nom"].lower().strip()
            PIECES_LUMIERES[nom] = entry["entity_id"]
            _HA_CUSTOM_KEYS["lumieres"].add(nom)
        for entry in custom.get("prises", []):
            nom = entry["nom"].lower().strip()
            PIECES_PRISES[nom] = entry["entity_id"]
            _HA_CUSTOM_KEYS["prises"].add(nom)
        for entry in custom.get("capteurs", []):
            nom = entry["nom"].lower().strip()
            PIECES_CAPTEURS[nom] = entry["entity_id"]
            _HA_CUSTOM_KEYS["capteurs"].add(nom)

    except Exception as e:
        print(f"[HA] Erreur chargement config : {e}")


_charger_config()


# ── API Home Assistant ─────────────────────────────────────────────────

def ha_appeler_service(domaine: str, service: str, entity_id: str, donnees: dict = None) -> bool:
    if not HA_URL or not HA_TOKEN:
        print("[HA] HA_URL ou HA_TOKEN non configuré dans .env ou jarvis_config.json")
        return False
    try:
        payload = {"entity_id": entity_id}
        if donnees:
            payload.update(donnees)
        r = requests.post(
            f"{HA_URL}/api/services/{domaine}/{service}",
            headers=HA_HEADERS, json=payload, timeout=5
        )
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"[HA] Erreur service : {e}")
        return False


def ha_get_etat(entity_id: str, attribut: str = None):
    if not HA_URL or not HA_TOKEN:
        return "inconnu"
    try:
        r    = requests.get(f"{HA_URL}/api/states/{entity_id}", headers=HA_HEADERS, timeout=5)
        data = r.json()
        if attribut:
            return data.get("attributes", {}).get(attribut, "inconnu")
        return data.get("state", "inconnu")
    except Exception as e:
        print(f"[HA] Erreur get état : {e}")
        return "inconnu"


def ha_lumiere(entity_id: str, etat: str = "on", luminosite: int = None, rgb: list = None) -> bool:
    service_name = "toggle" if etat == "toggle" else ("turn_on" if etat == "on" else "turn_off")
    donnees = {}
    if etat == "on":
        if luminosite is not None:
            donnees["brightness"] = int(luminosite)
        if rgb is not None:
            donnees["rgb_color"] = rgb
    return ha_appeler_service("light", service_name, entity_id, donnees)


def ha_interrupteur(entity_id: str, etat: str = "on") -> bool:
    return ha_appeler_service("switch", "turn_on" if etat == "on" else "turn_off", entity_id)


def ha_thermostat(entity_id: str, temperature: float) -> bool:
    return ha_appeler_service("climate", "set_temperature", entity_id, {"temperature": temperature})


# ── Météo (Open-Meteo, gratuit, sans clé) ─────────────────────────────

def _geocoder_ville(ville: str) -> tuple[float | None, float | None, str, str]:
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": ville, "count": 1, "language": "fr", "format": "json"},
            timeout=5,
        )
        data = r.json()
        if data.get("results"):
            res = data["results"][0]
            return res["latitude"], res["longitude"], res.get("name", ville), res.get("country", "")
    except Exception as e:
        print(f"[METEO] Erreur géocodage : {e}")
    return None, None, ville, ""


def get_meteo_actuelle(ville: str = None) -> str:
    """Retourne une phrase météo courte pour la synthèse vocale."""
    try:
        nom_ville = ville or VILLE_PAR_DEFAUT
        lat, lon, nom_affiche, _ = _geocoder_ville(nom_ville)
        if lat is None:
            lat, lon = LAT_PAR_DEFAUT, LON_PAR_DEFAUT
            nom_affiche = VILLE_PAR_DEFAUT
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat, "longitude": lon,
                "current":   "temperature_2m,apparent_temperature,weathercode,wind_speed_10m",
                "timezone":  "Europe/Paris",
            },
            timeout=8,
        )
        cur  = r.json()["current"]
        code = cur.get("weathercode", 0)
        temp = round(float(cur.get("temperature_2m", 0)))
        desc = CODES_METEO.get(code, "conditions inconnues")
        return f"À {nom_affiche}, il fait {temp} degrés et le ciel est {desc}."
    except Exception as e:
        print(f"[METEO] Erreur : {e}")
        return "Je n'arrive pas à récupérer la météo pour le moment."


def get_meteo_structuree(ville: str = None) -> dict | None:
    """Retourne les données météo structurées pour le panneau visuel frontend."""
    try:
        nom_ville = ville or VILLE_PAR_DEFAUT
        lat, lon, nom_affiche, _ = _geocoder_ville(nom_ville)
        if lat is None:
            lat, lon = LAT_PAR_DEFAUT, LON_PAR_DEFAUT
            nom_affiche = VILLE_PAR_DEFAUT
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat, "longitude": lon,
                "current":   "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weathercode",
                "timezone":  "Europe/Paris",
            },
            timeout=8,
        )
        cur  = r.json()["current"]
        code = cur.get("weathercode", 0)
        return {
            "ville":       nom_affiche,
            "temperature": round(float(cur.get("temperature_2m", 0))),
            "ressenti":    round(float(cur.get("apparent_temperature", 0))),
            "humidite":    round(float(cur.get("relative_humidity_2m", 0))),
            "vent":        round(float(cur.get("wind_speed_10m", 0))),
            "code":        code,
            "description": CODES_METEO.get(code, "inconnu"),
        }
    except Exception as e:
        print(f"[METEO] Erreur structurée : {e}")
        return None


def get_alertes_meteo(ville: str = None) -> str:
    """Retourne les alertes météo des 3 prochains jours."""
    try:
        nom_ville = ville or VILLE_PAR_DEFAUT
        lat, lon, nom_affiche, _ = _geocoder_ville(nom_ville)
        if lat is None:
            lat, lon, nom_affiche = LAT_PAR_DEFAUT, LON_PAR_DEFAUT, VILLE_PAR_DEFAUT
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily":    "weathercode,precipitation_sum,wind_speed_10m_max",
                "timezone": "Europe/Paris", "forecast_days": 3,
            },
            timeout=8,
        )
        daily   = r.json()["daily"]
        alertes = []
        for i in range(len(daily["weathercode"])):
            code  = daily["weathercode"][i]
            pluie = (daily.get("precipitation_sum") or [0, 0, 0])[i] or 0
            vent  = (daily.get("wind_speed_10m_max") or [0, 0, 0])[i] or 0
            jour  = ["aujourd'hui", "demain", "après-demain"][i]
            if code in [95, 96, 99]:
                alertes.append(f"Orage prévu {jour}")
            if code in [71, 73, 75, 85, 86]:
                alertes.append(f"Neige prévue {jour}")
            if pluie > 20:
                alertes.append(f"Fortes pluies {jour} ({pluie}mm)")
            if vent > 60:
                alertes.append(f"Vents forts {jour} ({vent} km/h)")
        if alertes:
            return "Alertes météo : " + ", ".join(alertes) + "."
        return f"Aucune alerte météo pour {nom_affiche} dans les 3 prochains jours."
    except Exception as e:
        return f"Impossible de vérifier les alertes météo : {e}"


# ── Dispatcher commandes vocales HA ───────────────────────────────────

def traiter_commande_ha(text: str) -> str | None:
    """Parse une commande vocale HA et retourne la réponse (None si non reconnue)."""
    t = text.lower()

    # Météo — géré en priorité même si HA non configuré
    if any(w in t for w in ["météo", "température extérieure", "quel temps"]):
        return get_meteo_actuelle()
    if "alerte" in t and "météo" in t:
        return get_alertes_meteo()

    # Lumières
    for nom, entity_id in PIECES_LUMIERES.items():
        if nom in t:
            # Couleur ?
            for couleur, rgb in COULEURS_MAP.items():
                if couleur in t:
                    ha_lumiere(entity_id, "on", rgb=rgb)
                    return f"Lumière {nom} en {couleur}."
            # Luminosité ?
            import re
            m = re.search(r"(\d+)\s*%", t)
            if m:
                brightness = int(int(m.group(1)) * 255 / 100)
                ha_lumiere(entity_id, "on", luminosite=brightness)
                return f"Luminosité {nom} à {m.group(1)}%."
            # On / Off / Toggle
            if any(w in t for w in ["allume", "active", "on", "mets"]):
                ok = ha_lumiere(entity_id, "on")
                return f"Lumière {nom} {'allumée' if ok else 'erreur'}."
            elif any(w in t for w in ["éteins", "coupe", "off", "arrête"]):
                ok = ha_lumiere(entity_id, "off")
                return f"Lumière {nom} {'éteinte' if ok else 'erreur'}."
            else:
                ok = ha_lumiere(entity_id, "toggle")
                return f"Lumière {nom} basculée."

    # Prises
    for nom, entity_id in PIECES_PRISES.items():
        if nom in t:
            etat = "on" if any(w in t for w in ["allume", "active", "branche"]) else "off"
            ha_interrupteur(entity_id, etat)
            return f"Prise {nom} {'activée' if etat == 'on' else 'désactivée'}."

    # Température d'une pièce
    for nom, entity_id in PIECES_CAPTEURS.items():
        if nom in t and any(w in t for w in ["température", "temp", "chaud", "froid", "degrés"]):
            valeur = ha_get_etat(entity_id)
            return f"Il fait {valeur} degrés dans {nom}."

    return None
