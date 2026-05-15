"""
Google Services — Docs, Gmail, Sheets, Calendar.
Développé par Morphoz.io — assistant personnel JARVIS.

Configuration : placez credentials.json dans ce dossier.
Suivez credentials_LISEZ_MOI.txt pour obtenir le fichier depuis Google Cloud Console.
"""
import base64
import os
import pickle
import webbrowser
from datetime import datetime, timezone
from email.mime.text import MIMEText

_DESKTOP_DIR = os.path.dirname(os.path.abspath(__file__))
_CREDS_PATH  = os.path.join(_DESKTOP_DIR, "credentials.json")
_TOKEN_PATH  = os.path.join(_DESKTOP_DIR, "token.pickle")

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

_google_ok = False
try:
    from google.oauth2.credentials import Credentials          # noqa: F401
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    _google_ok = True
except ImportError:
    pass

# Doc actif en session
dernier_doc_id:    str | None = None
dernier_doc_titre: str | None = None


# ── Authentification ──────────────────────────────────────────────────────────

def get_google_creds():
    if not _google_ok:
        print("[GOOGLE] google-auth-oauthlib non installé — pip install google-api-python-client google-auth-oauthlib")
        return None
    creds = None
    if os.path.exists(_TOKEN_PATH):
        with open(_TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(_CREDS_PATH):
                print("[GOOGLE] credentials.json introuvable — lisez credentials_LISEZ_MOI.txt")
                return None
            flow  = InstalledAppFlow.from_client_secrets_file(_CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return creds


def _service(api: str, version: str):
    creds = get_google_creds()
    if not creds:
        return None
    return build(api, version, credentials=creds)


def google_disponible() -> bool:
    return _google_ok and os.path.exists(_CREDS_PATH)


# ── Google Docs ───────────────────────────────────────────────────────────────

def creer_google_doc(titre: str = "Nouveau Document", contenu: str = "") -> str:
    global dernier_doc_id, dernier_doc_titre
    try:
        svc = _service("docs", "v1")
        if not svc:
            return "Google Docs non disponible. Vérifiez credentials.json, Harry."
        doc    = svc.documents().create(body={"title": titre}).execute()
        doc_id = doc["documentId"]
        dernier_doc_id    = doc_id
        dernier_doc_titre = titre
        if contenu:
            svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": contenu}}]},
            ).execute()
        webbrowser.open(f"https://docs.google.com/document/d/{doc_id}/edit")
        return f"Document '{titre}' créé et ouvert, Harry."
    except Exception as e:
        return f"Erreur Google Docs : {e}"


def modifier_google_doc(contenu: str, doc_id: str | None = None) -> str:
    global dernier_doc_id
    try:
        svc       = _service("docs", "v1")
        if not svc:
            return "Google Docs non disponible."
        target_id = doc_id or dernier_doc_id
        if not target_id:
            return "Aucun document ouvert en mémoire. Dites 'crée un document' d'abord."
        doc       = svc.documents().get(documentId=target_id).execute()
        end_index = doc["body"]["content"][-1]["endIndex"] - 1
        svc.documents().batchUpdate(
            documentId=target_id,
            body={"requests": [{"insertText": {"location": {"index": end_index}, "text": "\n" + contenu}}]},
        ).execute()
        webbrowser.open(f"https://docs.google.com/document/d/{target_id}/edit")
        return f"Texte ajouté dans '{dernier_doc_titre}', Harry."
    except Exception as e:
        return f"Erreur modification document : {e}"


def ouvrir_google_docs_accueil() -> str:
    webbrowser.open("https://docs.google.com")
    return "J'ouvre Google Docs, Harry."


# ── Gmail ─────────────────────────────────────────────────────────────────────

def lire_emails(max_results: int = 3) -> str:
    try:
        svc = _service("gmail", "v1")
        if not svc:
            return "Gmail non disponible. Vérifiez credentials.json, Harry."
        results  = svc.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            return "Votre boîte de réception est vide, Harry."
        lignes = []
        for msg in messages:
            m       = svc.users().messages().get(
                userId="me", id=msg["id"], format="metadata"
            ).execute()
            headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
            expediteur = headers.get("From", "?").split("<")[0].strip().strip('"')
            sujet      = headers.get("Subject", "Sans sujet")
            lignes.append(f"De {expediteur} : {sujet}")
        return f"Vos {len(lignes)} derniers emails, Harry : " + " | ".join(lignes)
    except Exception as e:
        return f"Erreur lecture Gmail : {e}"


def envoyer_email(destinataire: str, sujet: str, corps: str) -> str:
    try:
        svc = _service("gmail", "v1")
        if not svc:
            return "Gmail non disponible."
        msg            = MIMEText(corps)
        msg["to"]      = destinataire
        msg["subject"] = sujet
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email envoyé à {destinataire}, Harry."
    except Exception as e:
        return f"Erreur envoi email : {e}"


# ── Google Calendar ───────────────────────────────────────────────────────────

def lister_evenements_calendar(max_results: int = 5) -> str:
    try:
        svc    = _service("calendar", "v3")
        if not svc:
            return "Google Calendar non disponible. Vérifiez credentials.json, Harry."
        now    = datetime.now(timezone.utc).isoformat()
        events = svc.events().list(
            calendarId="primary", timeMin=now,
            maxResults=max_results, singleEvents=True, orderBy="startTime",
        ).execute()
        items = events.get("items", [])
        if not items:
            return "Aucun événement à venir dans votre agenda, Harry."
        lignes = []
        for e in items:
            start = e["start"].get("dateTime", e["start"].get("date", "?"))
            try:
                dt        = datetime.fromisoformat(start.replace("Z", "+00:00"))
                start_str = dt.strftime("%d/%m à %H:%M")
            except Exception:
                start_str = start
            lignes.append(f"{start_str} : {e.get('summary', 'Sans titre')}")
        return "Vos prochains événements, Harry : " + " | ".join(lignes)
    except Exception as e:
        return f"Erreur Google Calendar : {e}"


def creer_evenement_calendar(
    titre: str, debut_iso: str, fin_iso: str, description: str = ""
) -> str:
    try:
        svc = _service("calendar", "v3")
        if not svc:
            return "Google Calendar non disponible."
        event = {
            "summary":     titre,
            "description": description,
            "start":       {"dateTime": debut_iso, "timeZone": "Europe/Paris"},
            "end":         {"dateTime": fin_iso,   "timeZone": "Europe/Paris"},
        }
        svc.events().insert(calendarId="primary", body=event).execute()
        return f"Événement '{titre}' ajouté à votre agenda, Harry."
    except Exception as e:
        return f"Erreur création événement : {e}"


def ouvrir_google_calendar() -> str:
    webbrowser.open("https://calendar.google.com")
    return "J'ouvre Google Calendar, Harry."


# ── Google Sheets ─────────────────────────────────────────────────────────────

def creer_google_sheet(titre: str = "Nouvelle Feuille") -> str:
    try:
        svc      = _service("sheets", "v4")
        if not svc:
            return "Google Sheets non disponible. Vérifiez credentials.json, Harry."
        sheet    = svc.spreadsheets().create(
            body={"properties": {"title": titre}}
        ).execute()
        sheet_id = sheet["spreadsheetId"]
        webbrowser.open(f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
        return f"Feuille '{titre}' créée et ouverte, Harry."
    except Exception as e:
        return f"Erreur Google Sheets : {e}"


def ouvrir_google_sheets_accueil() -> str:
    webbrowser.open("https://sheets.google.com")
    return "J'ouvre Google Sheets, Harry."
