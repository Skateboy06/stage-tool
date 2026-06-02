import streamlit as st
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import time
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from bs4 import BeautifulSoup
import os
import json
import hashlib
from datetime import datetime, timedelta
import uuid
import random

# ─── ANTI-DÉTECTION CONFIG ────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]

REFERERS = [
    "https://www.google.fr/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.qwant.com/",
    "",
]

def get_headers_aleatoires():
    """Génère des headers aléatoires réalistes."""
    ua = random.choice(USER_AGENTS)
    referer = random.choice(REFERERS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(["fr-FR,fr;q=0.9,en;q=0.8", "fr-FR,fr;q=0.8,en-US;q=0.5", "fr,en;q=0.9"]),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none" if not referer else "cross-site",
        "Cache-Control": "max-age=0",
    }
    if referer:
        headers["Referer"] = referer
    return headers

def delai_humain(min_s=1.5, max_s=4.5):
    """Pause aléatoire pour simuler un comportement humain."""
    time.sleep(random.uniform(min_s, max_s))

# Session persistante avec cookies
_session = None
def get_session():
    global _session
    if _session is None:
        import requests as _requests
        _session = _requests.Session()
        _session.headers.update(get_headers_aleatoires())
    return _session

def requete_humaine(url, timeout=10, use_session=True):
    """Fait une requête HTTP en simulant un comportement humain."""
    try:
        headers = get_headers_aleatoires()
        if use_session:
            sess = get_session()
            sess.headers.update(headers)
            resp = sess.get(url, timeout=timeout, allow_redirects=True)
        else:
            resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        return resp
    except Exception:
        return None

# ─── PLAYWRIGHT / CAMOUFOX CONFIG ─────────────────────────────────────────────
PLAYWRIGHT_DISPONIBLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_DISPONIBLE = True
except ImportError:
    pass

CAMOUFOX_DISPONIBLE = False
try:
    from camoufox.sync_api import Camoufox
    CAMOUFOX_DISPONIBLE = True
except ImportError:
    pass

def scraper_avec_camoufox(url, timeout=15000):
    """Scrape une URL avec Camoufox - contourne les protections anti-bot avancées."""
    if not CAMOUFOX_DISPONIBLE:
        return None
    try:
        with Camoufox(headless=True) as fox:
            page = fox.new_page()
            page.set_extra_http_headers(get_headers_aleatoires())
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            # Simuler comportement humain
            page.mouse.move(random.randint(100, 500), random.randint(100, 400))
            time.sleep(random.uniform(0.5, 1.5))
            page.mouse.wheel(0, random.randint(200, 600))
            time.sleep(random.uniform(0.3, 1.0))
            html = page.content()
            page.close()
            return BeautifulSoup(html, "lxml")
    except Exception:
        return None

def scraper_avec_playwright(url, timeout=15000):
    """Scrape une URL avec Playwright - fallback si Camoufox indisponible."""
    if not PLAYWRIGHT_DISPONIBLE:
        return None
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": random.randint(1200, 1920), "height": random.randint(700, 1080)},
                locale="fr-FR",
                timezone_id="Europe/Paris",
            )
            page = context.new_page()
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            time.sleep(random.uniform(0.5, 2.0))
            html = page.content()
            browser.close()
            return BeautifulSoup(html, "lxml")
    except Exception:
        return None

def scraper_intelligent(url, timeout=10):
    """Essaie d'abord requests simple, puis Camoufox, puis Playwright si bloqué."""
    if not url:
        return None
    try:
        if not url.startswith("http"):
            url = "https://" + url
        # 1. Essai simple avec session + headers humains
        resp = requete_humaine(url, timeout=timeout)
        if resp and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            # Vérifier si on a été bloqué (page captcha/cloudflare vide)
            texte = soup.get_text()
            if len(texte) > 200 and not any(x in texte.lower() for x in ["captcha", "cloudflare", "access denied", "403 forbidden", "bot detected"]):
                return soup

        # 2. Si bloqué → Camoufox
        delai_humain(1, 3)
        soup = scraper_avec_camoufox(url)
        if soup:
            return soup

        # 3. Fallback → Playwright
        delai_humain(1, 2)
        return scraper_avec_playwright(url)

    except Exception:
        return None

# ─── SUPABASE CONFIG ──────────────────────────────────────────────────────────
SUPABASE_URL = "https://ilezjfqgfjdismxqnzjo.supabase.co"
SUPABASE_KEY = "sb_publishable_FqF6D8AL0vTb_X-oJdZ9QA_1bbM3aUM"

def get_supabase():
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

st.set_page_config(page_title="🎓 Outil Recherche de Stage", layout="wide")

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "entreprises" not in st.session_state:
    st.session_state.entreprises = []
if "profil_connecte" not in st.session_state:
    st.session_state.profil_connecte = None
if "relances_verifiees" not in st.session_state:
    st.session_state.relances_verifiees = False
if "relances_en_attente" not in st.session_state:
    st.session_state.relances_en_attente = []

# ─── CONSTANTES ───────────────────────────────────────────────────────────────
TRANCHES_SALARIES = {
    "NN": 0, "00": 0, "01": 2, "02": 5, "03": 10, "11": 15,
    "12": 25, "21": 50, "22": 75, "31": 150, "32": 250,
    "41": 375, "42": 750, "51": 1500, "52": 3500, "53": 7500
}
COLONNES_KANBAN = ["📋 À contacter", "📤 Contactée", "📬 Réponse reçue", "🤝 Entretien", "✅ Accepté", "❌ Refus"]
SUJET_RELANCE_DEFAULT = "Relance – Demande de stage d'immersion – {nom_entreprise}"
CORPS_RELANCE_DEFAULT = """Madame, Monsieur,

Je me permets de revenir vers vous suite à mon précédent email du {date_premier_contact}, dans lequel je sollicitais un stage d'immersion de deux semaines au sein de votre entreprise {nom_entreprise}.

N'ayant pas eu de retour de votre part, je souhaitais renouveler ma candidature et vous confirmer ma motivation intacte pour découvrir les métiers de votre secteur.

Je reste entièrement disponible pour en discuter à votre convenance.

Dans l'attente de votre retour, je vous adresse mes sincères salutations.

{prenom_nom}"""

# ─── FONCTIONS PROFIL ─────────────────────────────────────────────────────────
def get_profil_id(email):
    return hashlib.md5(email.strip().lower().encode()).hexdigest()

def get_historique_path(email):
    return f"historique_{get_profil_id(email)}.json"

def get_profil_path(email):
    return f"profil_{get_profil_id(email)}.json"

def charger_historique(email):
    profil_id = get_profil_id(email)
    # Essayer Supabase d'abord
    try:
        sb = get_supabase()
        if sb:
            res = sb.table("historique").select("nom, donnees").eq("profil_id", profil_id).execute()
            if res.data:
                return {row["nom"]: row["donnees"] for row in res.data}
    except Exception:
        pass
    # Fallback local
    path = get_historique_path(email)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def sauvegarder_historique(email, historique):
    profil_id = get_profil_id(email)
    # Sauvegarder sur Supabase
    try:
        sb = get_supabase()
        if sb:
            for cle, donnees in historique.items():
                sb.table("historique").upsert({
                    "id": f"{profil_id}_{cle[:50]}",
                    "profil_id": profil_id,
                    "nom": cle,
                    "donnees": donnees
                }).execute()
            # Supprimer les entrées qui ne sont plus dans l'historique
            res = sb.table("historique").select("nom").eq("profil_id", profil_id).execute()
            if res.data:
                noms_supabase = {row["nom"] for row in res.data}
                noms_locaux = set(historique.keys())
                a_supprimer = noms_supabase - noms_locaux
                for nom in a_supprimer:
                    sb.table("historique").delete().eq("profil_id", profil_id).eq("nom", nom).execute()
    except Exception:
        pass
    # Sauvegarder aussi en local comme backup
    with open(get_historique_path(email), "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

def charger_profil(email):
    profil_id = get_profil_id(email)
    # Essayer Supabase d'abord
    try:
        sb = get_supabase()
        if sb:
            res = sb.table("profils").select("donnees").eq("id", profil_id).execute()
            if res.data:
                return res.data[0]["donnees"]
    except Exception:
        pass
    # Fallback local
    path = get_profil_path(email)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def sauvegarder_profil(email, donnees):
    profil_id = get_profil_id(email)
    # Sauvegarder sur Supabase
    try:
        sb = get_supabase()
        if sb:
            sb.table("profils").upsert({
                "id": profil_id,
                "email": email,
                "donnees": donnees
            }).execute()
    except Exception:
        pass
    # Sauvegarder aussi en local comme backup
    with open(get_profil_path(email), "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)

def charger_modeles(email):
    return charger_profil(email).get("modeles_email", {})

def sauvegarder_modeles(email, modeles):
    profil = charger_profil(email)
    profil["modeles_email"] = modeles
    sauvegarder_profil(email, profil)

def marquer_contactees(email, entreprises_envoyees):
    historique = charger_historique(email)
    for e in entreprises_envoyees:
        cle = e["nom"].strip().lower()
        if cle not in historique:
            historique[cle] = {
                "id": str(uuid.uuid4()),
                "nom": e["nom"], "ville": e["ville"],
                "email": e["email"], "telephone": e.get("telephone", ""),
                "adresse": e.get("adresse", ""), "code_ape": e.get("code_ape", ""),
                "site_web": e.get("site_web", ""), "pages_jaunes": e.get("pages_jaunes", ""),
                "facebook": e.get("facebook", ""),
                "date_contact": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "date_contact_iso": datetime.now().isoformat(),
                "nb_relances": 0, "date_derniere_relance": "",
                "statut_kanban": "📤 Contactée", "repondu": False,
                "favori": False, "notes": "",
            }
        else:
            historique[cle].update({
                "email": e["email"], "site_web": e.get("site_web", ""),
                "pages_jaunes": e.get("pages_jaunes", ""), "facebook": e.get("facebook", ""),
            })
    sauvegarder_historique(email, historique)

def tranche_vers_effectif(tranche):
    return TRANCHES_SALARIES.get(str(tranche), 0)

# ─── FONCTIONS EMAIL ──────────────────────────────────────────────────────────
def envoyer_email(expediteur, mot_de_passe, destinataire, sujet, corps, chemin_cv=None):
    try:
        msg = MIMEMultipart()
        msg["From"] = expediteur
        msg["To"] = destinataire
        msg["Subject"] = sujet
        msg.attach(MIMEText(corps, "plain", "utf-8"))
        if chemin_cv and os.path.exists(chemin_cv):
            with open(chemin_cv, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(chemin_cv)}")
                msg.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(expediteur, mot_de_passe)
            server.sendmail(expediteur, destinataire, msg.as_string())
        return True
    except Exception as e:
        return str(e)

# ─── FONCTIONS SCRAPING ───────────────────────────────────────────────────────
def extraire_contact_site(url):
    if not url:
        return "", ""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        resp = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "lxml")
        texte = soup.get_text()
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", texte)
        emails = [e for e in emails if not e.endswith((".png", ".jpg", ".gif")) and "sentry" not in e]
        email = emails[0] if emails else ""
        tel_pattern = r"(?:(?:\+33|0033)[\s.\-]?[1-9]|0[1-9])(?:[\s.\-]?\d{2}){4}"
        tels = re.findall(tel_pattern, texte)
        tels_clean = []
        seen_tels = set()
        for t in tels:
            t_clean = re.sub(r"[\s.\-]", "", t)
            if t_clean not in seen_tels and len(t_clean) >= 10:
                seen_tels.add(t_clean)
                tels_clean.append(t)
        telephone = tels_clean[0] if tels_clean else ""
        return email, telephone
    except Exception:
        return "", ""

def chercher_mappy(nom, ville):
    """Cherche sur Mappy - très bien pour les artisans."""
    try:
        query = f"{nom} {ville}"
        url = f"https://fr.mappy.com/activite/{requests.utils.quote(nom.lower())}/{requests.utils.quote(ville.lower())}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        # Chercher directement le tel et email sur la page
        em, tel = extraire_depuis_soup(soup)
        if em or tel:
            return url, em, tel
        # Sinon chercher un lien vers la fiche
        lien = soup.find("a", href=re.compile(r"/poi/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://fr.mappy.com" + href
            return href, "", ""
    except Exception:
        pass
    return None, "", ""

def chercher_pappers(nom, ville):
    """Cherche sur Pappers - annuaire officiel des entreprises françaises."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.pappers.fr/recherche?q={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/entreprise/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.pappers.fr" + href
            # Scraper la fiche entreprise
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            em, tel = extraire_depuis_soup(soup2)
            return em, tel
    except Exception:
        pass
    return "", ""

def chercher_annuaire_tel(nom, ville):
    """Cherche sur tel.fr - annuaire téléphonique professionnel."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.tel.fr/recherche/{requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        # Chercher le premier résultat professionnel
        for a in soup.find_all("a", href=re.compile(r"/pro/")):
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.tel.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            em, tel = extraire_depuis_soup(soup2)
            if tel:
                return em, tel
    except Exception:
        pass
    return "", ""

def chercher_google_contact(nom, ville):
    """Cherche email et tel directement via Google en ciblant les résultats de contact."""
    try:
        # Cherche spécifiquement email ou contact
        for query_suffix in ["email contact", "téléphone contact", "site officiel"]:
            query = f"{nom} {ville} {query_suffix}"
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            resp = requete_humaine(url)
            soup = BeautifulSoup(resp.text, "lxml")
            texte = soup.get_text()
            # Chercher email dans les résultats Google directement
            emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", texte)
            emails = [e for e in emails if not any(x in e.lower() for x in EXCLUS_EMAIL + ["google", "goog"])]
            if emails:
                return emails[0], ""
            time.sleep(0.5)
    except Exception:
        pass
    return "", ""

def chercher_api_sirene(siren):
    """Cherche via l'API Sirene INSEE - source officielle."""
    try:
        url = f"https://api.insee.fr/entreprises/sirene/V3.11/siret?q=siren:{siren}&nombre=1"
        resp = requests.get(url, timeout=6, headers={**HEADERS_BROWSER, "Accept": "application/json"})
        data = resp.json()
        etablissements = data.get("etablissements", [])
        if etablissements:
            adresse = etablissements[0].get("adresseEtablissement", {})
            tel = adresse.get("numeroVoieEtablissement", "")
            return "", tel
    except Exception:
        pass
    return "", ""

def chercher_annuaire_gouv(nom, ville):
    """Cherche via l'API Annuaire des Entreprises data.gouv.fr."""
    try:
        url = f"https://recherche-entreprises.api.gouv.fr/search?q={requests.utils.quote(nom)}&departement=&limite=3"
        resp = requete_humaine(url)
        data = resp.json()
        for r in data.get("results", []):
            if ville.lower() in r.get("siege", {}).get("libelle_commune", "").lower():
                siege = r.get("siege", {})
                tel = siege.get("telephone", "") or ""
                email = siege.get("email", "") or ""
                # Essayer aussi le site web retourné
                site = r.get("site_web", "") or ""
                if site and not email:
                    em2, tel2 = extraire_contact_site(site)
                    if em2:
                        email = em2
                    if tel2 and not tel:
                        tel = tel2
                if tel or email:
                    return email, tel
    except Exception:
        pass
    return "", ""

def chercher_infobel(nom, ville):
    """Cherche sur Infobel.fr - annuaire pro français."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.infobel.com/fr/france/search/default.aspx?kw={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        em, tel = extraire_depuis_soup(soup)
        if tel or em:
            return em, tel
        # Chercher un lien vers la fiche
        lien = soup.find("a", href=re.compile(r"/fr/france/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.infobel.com" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_118712(nom, ville):
    """Cherche sur 118712.fr - annuaire téléphonique pro."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.118712.fr/recherche?quoi={requests.utils.quote(nom)}&ou={requests.utils.quote(ville)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        # Chercher le numéro directement
        em, tel = extraire_depuis_soup(soup)
        if tel:
            return em, tel
        # Chercher lien fiche
        lien = soup.find("a", href=re.compile(r"/fiche/|/pro/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.118712.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_cylex(nom, ville):
    """Cherche sur Cylex.fr - annuaire entreprises locales."""
    try:
        url = f"https://www.cylex.fr/recherche/{requests.utils.quote(nom.lower())}--{requests.utils.quote(ville.lower())}.html"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        em, tel = extraire_depuis_soup(soup)
        if tel or em:
            return em, tel
        lien = soup.find("a", href=re.compile(r"/company/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.cylex.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_hoodspot(nom, ville):
    """Cherche sur Hoodspot.fr - spécialisé artisans de proximité."""
    try:
        query = f"{nom} {ville}"
        url = f"https://hoodspot.fr/search?q={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/place/|/pro/|/entreprise/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://hoodspot.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_europages(nom, ville):
    """Cherche sur Europages.fr - annuaire B2B européen."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.europages.fr/entreprises/{requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/entreprise/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.europages.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_google_maps(nom, ville):
    """Cherche sur Google Maps (page publique) - très fiable pour artisans."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        texte = soup.get_text()
        # Chercher site web dans les données
        site_match = re.search(r'https?://(?!maps\.google|goo\.gl)[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s"<>]*)?', texte)
        site = site_match.group(0) if site_match else ""
        em, tel = extraire_depuis_soup(soup)
        if not tel:
            tels = re.findall(TEL_PATTERN, texte)
            tel = tels[0] if tels else ""
        return site, em, tel
    except Exception:
        pass
    return "", "", ""

def chercher_whois(domaine):
    """Cherche l'email dans les données Whois du domaine."""
    try:
        if not domaine:
            return ""
        # Nettoyer le domaine
        domaine = re.sub(r'https?://', '', domaine).split('/')[0].strip()
        url = f"https://www.whois.com/whois/{domaine}"
        resp = requete_humaine(url)
        texte = resp.text
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", texte)
        emails = [e for e in emails if not any(x in e.lower() for x in
                  EXCLUS_EMAIL + ["whois", "abuse", "privacy", "proxy", "protect"])]
        return emails[0] if emails else ""
    except Exception:
        pass
    return ""

def chercher_linkedin_dirigeant(nom_entreprise, nom_dirigeant, ville):
    """Cherche le profil LinkedIn du dirigeant."""
    try:
        query = f"{nom_dirigeant} {nom_entreprise} {ville} linkedin"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=True):
            if "linkedin.com/in/" in a["href"]:
                return a["href"]
    except Exception:
        pass
    return ""

def chercher_infogreffe(siren):
    """Cherche sur Infogreffe - Registre du Commerce."""
    try:
        url = f"https://www.infogreffe.fr/entreprise/{siren}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        em, tel = extraire_depuis_soup(soup)
        return em, tel
    except Exception:
        pass
    return "", ""

def chercher_devis_fr(nom, ville):
    """Cherche sur Devis.fr - artisans locaux."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.devis.fr/annuaire/recherche?q={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/annuaire/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.devis.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_qualibat(nom, ville):
    """Cherche sur Qualibat - entreprises certifiées RGE."""
    try:
        query = f"{nom} {ville}"
        url = f"https://qualibat.com/annuaire-des-entreprises/?s={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/entreprise/|/fiche/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://qualibat.com" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_cma(nom, ville):
    """Cherche dans l'annuaire de la Chambre des Métiers et de l'Artisanat."""
    try:
        query = f"{nom} {ville}"
        url = f"https://annuaire.artisanat.fr/recherche?q={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/fiche|/artisan|/entreprise"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://annuaire.artisanat.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_opencorporates(nom, ville):
    """Cherche sur OpenCorporates - base open source mondiale."""
    try:
        query = f"{nom}"
        url = f"https://opencorporates.com/companies/fr?q={requests.utils.quote(query)}&utf8=✓"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/companies/fr/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://opencorporates.com" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_dnb(nom, ville):
    """Cherche sur Dun & Bradstreet."""
    try:
        query = f"{nom} {ville} france"
        url = f"https://www.dnb.com/business-directory/company-search.html?SearchTerm={requests.utils.quote(query)}&CountryCode=FR"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/business-directory/company-profiles"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.dnb.com" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def deviner_emails_domaine(site_web, nom):
    """Génère et vérifie des emails probables à partir du domaine."""
    if not site_web:
        return ""
    try:
        domaine = re.sub(r'https?://', '', site_web).split('/')[0].strip()
        # Nettoyer le nom pour générer des variantes
        nom_clean = re.sub(r'[^a-zA-Z]', '', nom.lower())[:15]
        candidats = [
            f"contact@{domaine}",
            f"info@{domaine}",
            f"bonjour@{domaine}",
            f"accueil@{domaine}",
            f"devis@{domaine}",
            f"{nom_clean}@{domaine}",
        ]
        for email_candidat in candidats:
            if verifier_email_smtp(email_candidat):
                return email_candidat
    except Exception:
        pass
    return ""

def verifier_email_smtp(email):
    """Vérifie si un email existe via SMTP sans envoyer de message."""
    try:
        domaine = email.split("@")[1]
        import dns.resolver
        records = dns.resolver.resolve(domaine, 'MX')
        mx = sorted(records, key=lambda r: r.preference)[0].exchange.to_text()
        with smtplib.SMTP(timeout=5) as smtp:
            smtp.connect(mx, 25)
            smtp.helo("check.local")
            smtp.mail("check@check.local")
            code, _ = smtp.rcpt(email)
            return code == 250
    except Exception:
        pass
    return False

def chercher_google_maps(nom, ville):
    """Cherche sur Google Maps via la page publique."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        em, tel = extraire_depuis_soup(soup)
        # Chercher aussi le site web dans la page
        site = ""
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "google" not in href and "maps" not in href:
                site = href
                break
        return em, tel, site
    except Exception:
        pass
    return "", "", ""

def chercher_cma(nom, ville):
    """Cherche sur l'annuaire de la Chambre des Métiers (CMA)."""
    try:
        url = f"https://www.artisanat.fr/trouver-un-artisan?search={requests.utils.quote(nom)}&location={requests.utils.quote(ville)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        em, tel = extraire_depuis_soup(soup)
        if tel or em:
            return em, tel
        lien = soup.find("a", href=re.compile(r"/artisan/|/fiche/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.artisanat.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_qualibat(nom, ville):
    """Cherche sur Qualibat - label RGE entreprises BTP."""
    try:
        url = f"https://qualibat.com/annuaire/?search={requests.utils.quote(nom)}&city={requests.utils.quote(ville)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/entreprise/|/fiche/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://qualibat.com" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_faire_gouv(nom, ville):
    """Cherche sur faire.gouv.fr - annuaire RGE officiel."""
    try:
        url = f"https://www.faire.gouv.fr/trouver-un-professionnel?businessName={requests.utils.quote(nom)}&city={requests.utils.quote(ville)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        em, tel = extraire_depuis_soup(soup)
        if tel or em:
            return em, tel
        lien = soup.find("a", href=re.compile(r"/professionnel/|/entreprise/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.faire.gouv.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_devis_fr(nom, ville):
    """Cherche sur Devis.fr - mise en relation artisans."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.devis.fr/annuaire/?q={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/artisan/|/entreprise/|/pro/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.devis.fr" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_infogreffe(siren):
    """Cherche sur Infogreffe - Registre du Commerce."""
    try:
        url = f"https://www.infogreffe.fr/entreprise/{siren}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        return extraire_depuis_soup(soup)
    except Exception:
        pass
    return "", ""

def chercher_whois(site_web):
    """Cherche l'email dans les données Whois du domaine."""
    try:
        if not site_web:
            return ""
        # Extraire le domaine
        domain = re.sub(r"https?://", "", site_web).split("/")[0].strip()
        url = f"https://www.whois.com/whois/{domain}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        texte = soup.get_text()
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", texte)
        emails = [e for e in emails if not any(x in e.lower() for x in EXCLUS_EMAIL + ["whois", "abuse", "privacy"])]
        return emails[0] if emails else ""
    except Exception:
        pass
    return ""

def chercher_linkedin_dirigeant(nom_entreprise, nom_dirigeant):
    """Cherche le contact du dirigeant sur LinkedIn."""
    try:
        if not nom_dirigeant:
            return "", ""
        query = f"{nom_dirigeant} {nom_entreprise} linkedin"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=True):
            if "linkedin.com/in/" in a["href"]:
                return a["href"], ""
    except Exception:
        pass
    return "", ""

def chercher_opencorporates(nom, ville):
    """Cherche sur OpenCorporates - base mondiale open source."""
    try:
        url = f"https://opencorporates.com/companies/fr?q={requests.utils.quote(nom)}&utf8=✓"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/companies/fr/"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://opencorporates.com" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_dnb(nom, ville):
    """Cherche sur Dun & Bradstreet."""
    try:
        url = f"https://www.dnb.com/business-directory/company-search.html?searchTerm={requests.utils.quote(nom)}&location={requests.utils.quote(ville)}"
        resp = requete_humaine(url)
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", href=re.compile(r"/business-directory/company-profiles"))
        if lien:
            href = lien["href"]
            if not href.startswith("http"):
                href = "https://www.dnb.com" + href
            resp2 = requete_humaine(href)
            soup2 = BeautifulSoup(resp2.text, "lxml")
            return extraire_depuis_soup(soup2)
    except Exception:
        pass
    return "", ""

def chercher_site_direct(nom, ville):
    """Tente de deviner directement le domaine de l'entreprise."""
    try:
        # Nettoyer le nom pour créer des variantes de domaine
        nom_clean = nom.lower()
        nom_clean = re.sub(r"[^a-z0-9\s]", "", nom_clean).strip()
        mots = nom_clean.split()
        ville_clean = ville.lower().replace(" ", "-")

        # Générer des variantes de domaine
        variantes = []
        if mots:
            base = "-".join(mots[:3])  # ex: dupont-btp-nord
            variantes += [
                f"{base}.fr", f"{base}.com",
                f"{mots[0]}.fr", f"{mots[0]}.com",
                f"{base}-{ville_clean}.fr",
                f"{mots[0]}-{ville_clean}.fr",
            ]
            if len(mots) >= 2:
                variantes += [
                    f"{mots[0]}-{mots[1]}.fr",
                    f"{mots[0]}-{mots[1]}.com",
                ]

        for domaine in variantes:
            try:
                url = f"https://{domaine}"
                resp = requete_humaine(url, timeout=5)
                if resp and resp.status_code == 200:
                    return url
            except Exception:
                continue
    except Exception:
        pass
    return None

def chercher_crt_sh(nom):
    """Cherche le domaine via les certificats SSL sur crt.sh."""
    try:
        nom_clean = nom.lower().split()[0]  # Premier mot du nom
        url = f"https://crt.sh/?q=%25{requests.utils.quote(nom_clean)}%25&output=json"
        resp = requete_humaine(url, timeout=8)
        if resp and resp.status_code == 200:
            data = resp.json()
            domaines = set()
            for entry in data[:20]:
                nom_domaine = entry.get("name_value", "")
                # Filtrer les domaines français pertinents
                for ligne in nom_domaine.split("\n"):
                    ligne = ligne.strip().replace("*.", "")
                    if ligne.endswith(".fr") or ligne.endswith(".com"):
                        domaines.add(ligne)
            if domaines:
                # Tester le premier domaine trouvé
                for d in list(domaines)[:5]:
                    try:
                        url_test = f"https://{d}"
                        resp2 = requete_humaine(url_test, timeout=5)
                        if resp2 and resp2.status_code == 200:
                            return url_test
                    except Exception:
                        continue
    except Exception:
        pass
    return None

def chercher_viewdns(nom_dirigeant):
    """Cherche les domaines via Whois inversé sur viewdns.info."""
    try:
        if not nom_dirigeant:
            return None
        url = f"https://viewdns.info/reversewhois/?q={requests.utils.quote(nom_dirigeant)}"
        soup = scraper_intelligent(url)
        if soup:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".fr" in href or ".com" in href:
                    domaine = re.sub(r"https?://", "", href).split("/")[0]
                    if domaine:
                        return f"https://{domaine}"
    except Exception:
        pass
    return None

def chercher_verif_com(siren):
    """Cherche le site web via verif.com avec le SIREN."""
    try:
        if not siren:
            return None
        url = f"https://www.verif.com/societe/{siren}"
        soup = scraper_intelligent(url)
        if soup:
            em, tel = extraire_depuis_soup(soup)
            # Chercher le site web
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and not any(x in href for x in ["verif.com", "google", "facebook"]):
                    return href, em, tel
    except Exception:
        pass
    return None, "", ""

def chercher_pappers_site(nom, ville):
    """Cherche le site web via Pappers."""
    try:
        url = f"https://www.pappers.fr/recherche?q={requests.utils.quote(nom + ' ' + ville)}"
        soup = scraper_intelligent(url)
        if soup:
            lien = soup.find("a", href=re.compile(r"/entreprise/"))
            if lien:
                href = lien["href"]
                if not href.startswith("http"):
                    href = "https://www.pappers.fr" + href
                delai_humain(0.5, 1.5)
                soup2 = scraper_intelligent(href)
                if soup2:
                    # Chercher le site web dans la fiche
                    for a in soup2.find_all("a", href=True):
                        href2 = a["href"]
                        if href2.startswith("http") and "pappers" not in href2:
                            return href2
    except Exception:
        pass
    return None

def chercher_societe_site(nom, ville):
    """Cherche le site web via Societe.com."""
    try:
        url = f"https://www.societe.com/cgi-bin/search?champs={requests.utils.quote(nom + ' ' + ville)}"
        soup = scraper_intelligent(url)
        if soup:
            lien = soup.find("a", href=re.compile(r"/societe/"))
            if lien:
                href = lien["href"]
                if not href.startswith("http"):
                    href = "https://www.societe.com" + href
                delai_humain(0.5, 1.5)
                soup2 = scraper_intelligent(href)
                if soup2:
                    for a in soup2.find_all("a", href=True):
                        href2 = a["href"]
                        if href2.startswith("http") and "societe.com" not in href2:
                            return href2
    except Exception:
        pass
    return None

def chercher_kompass_site(nom, ville):
    """Cherche le site web via Kompass."""
    try:
        url = f"https://fr.kompass.com/searchCompanies?text={requests.utils.quote(nom + ' ' + ville)}"
        soup = scraper_intelligent(url)
        if soup:
            lien = soup.find("a", href=re.compile(r"/c/"))
            if lien:
                href = lien["href"]
                if not href.startswith("http"):
                    href = "https://fr.kompass.com" + href
                delai_humain(0.5, 1.5)
                soup2 = scraper_intelligent(href)
                if soup2:
                    for a in soup2.find_all("a", href=True):
                        href2 = a["href"]
                        if href2.startswith("http") and "kompass" not in href2:
                            return href2
    except Exception:
        pass
    return None

def chercher_linkedin_site(nom, ville):
    """Cherche le site web via la page LinkedIn de l'entreprise."""
    try:
        query = f"{nom} {ville} site:linkedin.com/company"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        soup = scraper_intelligent(url)
        if soup:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "linkedin.com/company" in href:
                    if not href.startswith("http"):
                        href = href.split("/url?q=")[-1].split("&")[0]
                    delai_humain(1, 2)
                    soup2 = scraper_intelligent(href)
                    if soup2:
                        for a2 in soup2.find_all("a", href=True):
                            href2 = a2["href"]
                            if href2.startswith("http") and "linkedin" not in href2:
                                return href2
    except Exception:
        pass
    return None

def chercher_similarweb(nom, ville, code_ape):
    """Cherche via SimilarWeb par secteur et ville."""
    try:
        # Convertir code APE en secteur pour similarweb
        secteurs = {
            "43": "construction", "41": "construction",
            "81": "landscaping", "45": "automotive",
            "25": "manufacturing"
        }
        code_court = code_ape[:2] if code_ape else ""
        secteur = secteurs.get(code_court, "business-services")
        url = f"https://www.similarweb.com/fr/top-websites/france/{secteur}/"
        # Trop générique pour être utile, on cherche plutôt via Google
        query = f'site:similarweb.com "{nom}" "{ville}"'
        url2 = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        soup = scraper_intelligent(url2)
        if soup:
            for a in soup.find_all("a", href=True):
                if "similarweb.com/website/" in a["href"]:
                    href = a["href"].split("/url?q=")[-1].split("&")[0]
                    domaine = href.replace("https://www.similarweb.com/website/", "").split("/")[0]
                    if domaine:
                        return f"https://{domaine}"
    except Exception:
        pass
    return None

def chercher_site_tentative_directe(nom, ville):
    """Tente directement des URLs probables basées sur le nom de l'entreprise."""
    try:
        # Nettoyer le nom pour créer des domaines probables
        nom_clean = nom.lower()
        nom_clean = re.sub(r"[^a-z0-9\s-]", "", nom_clean)
        nom_clean = re.sub(r"\s+", "-", nom_clean.strip())
        # Raccourcir si trop long
        mots = nom_clean.split("-")[:3]
        nom_court = "-".join(mots)
        ville_clean = re.sub(r"[^a-z0-9]", "", ville.lower())

        candidats = [
            f"https://www.{nom_court}.fr",
            f"https://www.{nom_court}.com",
            f"https://{nom_court}.fr",
            f"https://{nom_court}.com",
            f"https://www.{nom_court}-{ville_clean}.fr",
            f"https://{nom_court}-{ville_clean}.fr",
        ]
        for url in candidats:
            try:
                resp = requete_humaine(url, timeout=5)
                if resp and resp.status_code == 200 and len(resp.text) > 500:
                    return url
            except Exception:
                continue
    except Exception:
        pass
    return None

def chercher_crt_sh(nom):
    """Cherche le domaine via les certificats SSL sur crt.sh."""
    try:
        # Prendre les 2-3 premiers mots du nom
        mots = nom.lower().split()[:2]
        query = " ".join(mots)
        url = f"https://crt.sh/?q={requests.utils.quote(query)}&output=json"
        resp = requete_humaine(url, timeout=8)
        if resp and resp.status_code == 200:
            data = resp.json()
            domaines = set()
            for cert in data[:20]:
                name = cert.get("name_value", "")
                for d in name.split("\n"):
                    d = d.strip().lstrip("*.")
                    if d and "." in d and len(d) < 50:
                        # Filtrer les domaines generiques
                        if not any(x in d for x in ["google", "cloudflare", "amazonaws", "microsoft"]):
                            domaines.add(d)
            # Tester chaque domaine trouvé
            for domaine in list(domaines)[:5]:
                url_test = f"https://{domaine}"
                try:
                    resp2 = requete_humaine(url_test, timeout=5)
                    if resp2 and resp2.status_code == 200:
                        # Vérifier que la page mentionne le nom de l'entreprise
                        if any(mot in resp2.text.lower() for mot in nom.lower().split()[:2]):
                            return url_test
                except Exception:
                    continue
    except Exception:
        pass
    return None

def chercher_viewdns_whois(nom_dirigeant):
    """Cherche les domaines enregistrés au nom du dirigeant via ViewDNS."""
    try:
        if not nom_dirigeant:
            return None
        url = f"https://viewdns.info/reversewhois/?q={requests.utils.quote(nom_dirigeant)}"
        soup = scraper_intelligent(url)
        if soup:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".fr" in href or ".com" in href:
                    if href.startswith("http"):
                        return href
    except Exception:
        pass
    return None

def chercher_verif_com(siren):
    """Cherche sur verif.com via le SIREN."""
    try:
        if not siren:
            return None, "", ""
        url = f"https://www.verif.com/societe/{siren}"
        soup = scraper_intelligent(url)
        if soup:
            em, tel = extraire_depuis_soup(soup)
            # Chercher le site web
            site = ""
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and "verif.com" not in href and "google" not in href:
                    site = href
                    break
            return site, em, tel
    except Exception:
        pass
    return None, "", ""

def chercher_societe_ninja(siren):
    """Cherche sur societe.ninja via le SIREN."""
    try:
        if not siren:
            return None, "", ""
        url = f"https://societe.ninja/{siren}"
        soup = scraper_intelligent(url)
        if soup:
            em, tel = extraire_depuis_soup(soup)
            site = ""
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and "societe.ninja" not in href:
                    site = href
                    break
            return site, em, tel
    except Exception:
        pass
    return None, "", ""

def chercher_linkedin_entreprise(nom, ville):
    """Cherche la page LinkedIn de l'entreprise."""
    try:
        query = f"{nom} {ville} linkedin"
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requete_humaine(url, timeout=8)
        if resp:
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "linkedin.com/company/" in href:
                    if not href.startswith("http"):
                        href = href.split("/url?q=")[1].split("&")[0] if "/url?q=" in href else href
                    return href
    except Exception:
        pass
    return None

def chercher_similarweb(nom, ville):
    """Cherche sur SimilarWeb pour trouver le domaine."""
    try:
        query = f"{nom} {ville}"
        url = f"https://www.similarweb.com/fr/website-search/?query={requests.utils.quote(query)}"
        soup = scraper_intelligent(url)
        if soup:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/website/" in href and "similarweb" not in href:
                    domaine = href.split("/website/")[-1].strip("/")
                    if domaine:
                        return f"https://{domaine}"
    except Exception:
        pass
    return None

def deviner_emails(site_web):
    """Génère et vérifie les emails probables via SMTP."""
    if not site_web:
        return ""
    try:
        domain = re.sub(r"https?://", "", site_web).split("/")[0].strip()
        if not domain:
            return ""
        candidats = [
            f"contact@{domain}", f"info@{domain}", f"bonjour@{domain}",
            f"accueil@{domain}", f"pro@{domain}", f"devis@{domain}",
        ]
        import smtplib as _smtp
        for email_candidat in candidats:
            try:
                mx_domain = domain
                server = _smtp.SMTP(timeout=5)
                server.connect("smtp.gmail.com", 25)
                server.helo("check.com")
                server.mail("check@check.com")
                code, _ = server.rcpt(email_candidat)
                server.quit()
                if code == 250:
                    return email_candidat
            except Exception:
                # Si SMTP bloqué, retourner le premier candidat probable
                return f"contact@{domain}"
    except Exception:
        pass
    return ""

def extraire_email_site(url):
    email, _ = extraire_contact_site(url)
    return email

def chercher_site_google(nom, ville):
    try:
        query = f"{nom} {ville} site officiel"
        url_s = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requests.get(url_s, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "lxml")
        EXCLUS = ["google", "facebook", "pagesjaunes", "societe.com", "pappers", "infogreffe", "linkedin", "youtube", "wikipedia"]
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/url?q=" in href:
                real_url = href.split("/url?q=")[1].split("&")[0]
                if real_url.startswith("http") and not any(d in real_url for d in EXCLUS):
                    return real_url
    except Exception:
        pass
    return None

def chercher_pages_jaunes(nom, ville):
    try:
        query = f"{nom} {ville}"
        url_s = f"https://www.pagesjaunes.fr/annuaire/chercherlespros?quoiqui={requests.utils.quote(query)}"
        resp = requests.get(url_s, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "lxml")
        lien = soup.find("a", {"class": re.compile("bi-denomination")})
        if lien and lien.get("href"):
            return "https://www.pagesjaunes.fr" + lien["href"]
    except Exception:
        pass
    return None

def chercher_facebook(nom, ville):
    try:
        query = f"{nom} {ville} facebook"
        url_s = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requests.get(url_s, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "lxml")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/url?q=" in href:
                real_url = href.split("/url?q=")[1].split("&")[0]
                if "facebook.com" in real_url:
                    return real_url
    except Exception:
        pass
    return None

# ─── RECHERCHE ENTREPRISES ────────────────────────────────────────────────────
def geocode_adresse(adresse):
    geolocator = Nominatim(user_agent="stage_tool_v3")
    location = geolocator.geocode(adresse)
    if location:
        return (location.latitude, location.longitude)
    return None

def rechercher_entreprises(codes_ape, coords_ref, rayon_km, max_results, min_salaries, max_salaries, email_profil):
    entreprises = []
    historique = charger_historique(email_profil) if email_profil else {}
    for code_ape in codes_ape:
        code_ape = code_ape.strip().upper()
        page = 1
        while len(entreprises) < max_results:
            url = "https://recherche-entreprises.api.gouv.fr/search"
            params = {"activite_principale": code_ape, "per_page": 25, "page": page, "etat_administratif": "A"}
            try:
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()
            except Exception as e:
                st.warning(f"Erreur API pour {code_ape} : {e}")
                break
            resultats = data.get("results", [])
            if not resultats:
                break
            for r in resultats:
                try:
                    siege = r.get("siege", {})
                    lat = siege.get("latitude")
                    lon = siege.get("longitude")
                    if lat and lon:
                        dist = geodesic(coords_ref, (float(lat), float(lon))).km
                        if dist <= rayon_km:
                            tranche = r.get("tranche_effectif_salarie") or siege.get("tranche_effectif_salarie") or "00"
                            effectif = tranche_vers_effectif(tranche)
                            if effectif < min_salaries or effectif > max_salaries:
                                continue
                            nom = r.get("nom_complet", "")
                            cle = nom.strip().lower()
                            hist_entry = historique.get(cle, {})
                            entreprises.append({
                                "nom": nom,
                                "ville": siege.get("libelle_commune", ""),
                                "code_ape": r.get("activite_principale", ""),
                                "siren": r.get("siren", ""),
                                "adresse": siege.get("adresse", ""),
                                "site_web": hist_entry.get("site_web") or r.get("site_web", "") or "",
                                "pages_jaunes": hist_entry.get("pages_jaunes", ""),
                                "facebook": hist_entry.get("facebook", ""),
                                "linkedin": hist_entry.get("linkedin", ""),
                                "email": hist_entry.get("email", ""),
                                "telephone": hist_entry.get("telephone") or siege.get("telephone", "") or "",
                                "repondu": "Non", "j_ai_repondu": "Non",
                                "distance_km": round(dist, 1),
                                "effectif_approx": effectif,
                                "deja_contactee": cle in historique,
                                "date_contact": hist_entry.get("date_contact", ""),
                                "favori": hist_entry.get("favori", False),
                                "statut_kanban": hist_entry.get("statut_kanban", "📋 À contacter"),
                                "lat": float(lat), "lon": float(lon),
                            })
                except Exception:
                    continue
            if page >= data.get("total_pages", 1):
                break
            page += 1
            time.sleep(0.3)
    seen = set()
    unique = []
    for e in entreprises:
        if e["nom"] not in seen:
            seen.add(e["nom"])
            unique.append(e)
    return sorted(unique, key=lambda x: (not x["favori"], x["deja_contactee"], x["distance_km"]))

# ─── EXCEL ────────────────────────────────────────────────────────────────────
def generer_excel(entreprises, filepath):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Candidatures"
    headers = ["Nom", "Ville", "APE", "Répondu ?", "J'ai répondu ?", "Email", "Téléphone",
               "Adresse", "Distance (km)", "Effectif", "Déjà contactée ?", "Date contact",
               "Statut", "Favori ⭐", "Site web", "Pages Jaunes", "Facebook"]
    header_fill = PatternFill("solid", fgColor="2E86AB")
    grey_fill = PatternFill("solid", fgColor="DDDDDD")
    yellow_fill = PatternFill("solid", fgColor="FFF9C4")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")
    for row, e in enumerate(entreprises, 2):
        vals = [e["nom"], e["ville"], e["code_ape"], e.get("repondu","Non"), e.get("j_ai_repondu","Non"),
                e["email"], e["telephone"], e["adresse"], e["distance_km"], e.get("effectif_approx",""),
                "Oui" if e.get("deja_contactee") else "Non", e.get("date_contact",""),
                e.get("statut_kanban",""), "⭐" if e.get("favori") else "",
                e.get("site_web",""), e.get("pages_jaunes",""), e.get("facebook","")]
        fill = yellow_fill if e.get("favori") else (grey_fill if e.get("deja_contactee") else None)
        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=row, column=col, value=val)
            if fill:
                cell.fill = fill
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
    wb.save(filepath)

# ─── VÉRIFICATION RELANCES ────────────────────────────────────────────────────
if st.session_state.profil_connecte and not st.session_state.relances_verifiees:
    p = st.session_state.profil_connecte
    if p.get("relance_auto", False):
        historique = charger_historique(p["email"])
        delai_jours = int(p.get("relance_delai", 7))
        nb_max_relances = int(p.get("relance_nb_max", 1))
        relances_en_attente = []
        for cle, e in historique.items():
            if e.get("repondu") or e.get("nb_relances", 0) >= nb_max_relances or not e.get("email"):
                continue
            date_ref_str = e.get("date_derniere_relance") or e.get("date_contact_iso", "")
            if not date_ref_str:
                continue
            try:
                date_ref = datetime.fromisoformat(date_ref_str)
                jours_ecoules = (datetime.now() - date_ref).days
                if jours_ecoules >= delai_jours:
                    relances_en_attente.append({**e, "jours_ecoules": jours_ecoules})
            except Exception:
                continue
        st.session_state.relances_en_attente = relances_en_attente
    st.session_state.relances_verifiees = True

# ─── INTERFACE ────────────────────────────────────────────────────────────────
st.title("🎓 Outil de Recherche de Stage")
st.markdown("---")

# ─── POPUP RELANCES ───────────────────────────────────────────────────────────
if st.session_state.profil_connecte and st.session_state.relances_en_attente:
    p = st.session_state.profil_connecte
    relances = st.session_state.relances_en_attente
    st.warning(f"🔔 **{len(relances)} relance(s) en attente !** Choisis lesquelles envoyer :")
    selections = {}
    for e in relances:
        selections[e["nom"]] = st.checkbox(
            f"**{e['nom']}** — {e.get('ville','')} — contactée il y a **{e['jours_ecoules']} jours**",
            value=True, key=f"relance_check_{e['nom'][:20]}"
        )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Envoyer les relances sélectionnées", type="primary"):
            a_envoyer = [e for e in relances if selections.get(e["nom"], False)]
            if not a_envoyer:
                st.warning("Aucune relance sélectionnée.")
            else:
                historique = charger_historique(p["email"])
                succes, echecs = 0, 0
                for e in a_envoyer:
                    sujet_p = p.get("sujet_relance", SUJET_RELANCE_DEFAULT).replace("{nom_entreprise}", e["nom"])
                    corps_p = p.get("corps_relance", CORPS_RELANCE_DEFAULT).replace("{nom_entreprise}", e["nom"])
                    corps_p = corps_p.replace("{ville}", e.get("ville","")).replace("{prenom_nom}", p.get("nom",""))
                    corps_p = corps_p.replace("{date_premier_contact}", e.get("date_contact",""))
                    result = envoyer_email(p["email"], p["mdp"], e["email"], sujet_p, corps_p)
                    if result is True:
                        cle = e["nom"].strip().lower()
                        if cle in historique:
                            historique[cle]["nb_relances"] = e.get("nb_relances", 0) + 1
                            historique[cle]["date_derniere_relance"] = datetime.now().isoformat()
                        succes += 1
                    else:
                        echecs += 1
                sauvegarder_historique(p["email"], historique)
                st.session_state.relances_en_attente = []
                st.success(f"✅ {succes} relance(s) envoyée(s) !")
                if echecs:
                    st.warning(f"⚠️ {echecs} échec(s).")
                st.rerun()
    with col2:
        if st.button("🚫 Ignorer pour cette session"):
            st.session_state.relances_en_attente = []
            st.rerun()
    st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "👤 Profil", "🔍 Recherche", "📋 Kanban", "📧 Emails", "🗺️ Carte", "📈 Statistiques", "📊 Export Excel"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — PROFIL
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.header("👤 Connexion à ton profil")
    st.info("Ton profil sauvegarde tous tes paramètres automatiquement.")

    col1, col2 = st.columns(2)
    with col1:
        profil_email_input = st.text_input("📧 Ton adresse Gmail", placeholder="toi@gmail.com", key="profil_email_input")
    with col2:
        profil_mdp_input = st.text_input("🔑 Mot de passe d'application", type="password", key="profil_mdp_input")

    if st.button("🔓 Se connecter / Créer le profil", type="primary"):
        if not profil_email_input or not profil_mdp_input:
            st.error("Remplis les deux champs !")
        else:
            profil_data = charger_profil(profil_email_input)
            st.session_state.profil_connecte = {"email": profil_email_input, "mdp": profil_mdp_input, **profil_data}
            st.session_state.relances_verifiees = False
            historique = charger_historique(profil_email_input)
            st.success(f"✅ Profil chargé pour **{profil_email_input}**")
            st.info(f"📬 **{len(historique)}** entreprise(s) dans ton historique.")

    if st.session_state.profil_connecte:
        p = st.session_state.profil_connecte
        st.markdown("---")
        st.subheader("⚙️ Mes paramètres")

        col1, col2 = st.columns(2)
        with col1:
            p_nom = st.text_input("👤 Prénom et nom", value=p.get("nom",""), placeholder="Jean Dupont", key="profil_nom")
            p_situation = st.text_input("🎓 Situation", value=p.get("situation",""), placeholder="En définition de projet", key="profil_situation")
            p_adresse = st.text_input("📍 Adresse de référence", value=p.get("adresse",""), placeholder="Richebourg, 62", key="profil_adresse")
            p_rayon = st.number_input("📏 Rayon (km)", min_value=1, max_value=100, value=int(p.get("rayon", 20)))
        with col2:
            p_codes_ape = st.text_area("🏭 Codes APE/NAF", value=p.get("codes_ape",""), placeholder="43.31Z\n81.30Z", height=120, key="profil_codes_ape")
            p_min_sal = st.number_input("👥 Salariés minimum", min_value=0, max_value=10000, value=int(p.get("min_sal", 1)))
            p_max_sal = st.number_input("👥 Salariés maximum", min_value=1, max_value=10000, value=int(p.get("max_sal", 50)))
            p_max_entreprises = st.number_input("🔢 Nombre max d'entreprises", min_value=10, max_value=500, value=int(p.get("max_entreprises", 100)))

        st.markdown("#### ✉️ Modèle email principal")
        p_sujet = st.text_input("Sujet", value=p.get("sujet","Demande de stage d'immersion – {nom_entreprise}"), key="profil_sujet")
        p_corps = st.text_area("Corps", value=p.get("corps", """Madame, Monsieur,

Je me permets de vous contacter afin de solliciter un stage d'immersion de deux semaines au sein de votre entreprise {nom_entreprise}, basée à {ville}.

Actuellement en définition de projet professionnel, je souhaite découvrir les métiers de votre secteur d'activité afin de mieux orienter mon parcours professionnel.

Sérieux(se), autonome et motivé(e), je suis prêt(e) à m'investir pleinement aux côtés de vos équipes. Ce stage ne représente aucune contrainte administrative ni financière pour votre entreprise.

Je reste disponible pour en discuter par téléphone ou par email, à votre convenance.

Dans l'attente de votre retour, je vous adresse mes sincères salutations.

{prenom_nom}"""), height=220, key="profil_corps")

        st.markdown("#### 📚 Modèles d'emails supplémentaires")
        st.caption("Crée des modèles par secteur et associe-leur des codes APE pour un envoi automatique.")
        modeles = charger_modeles(p["email"])
        if modeles:
            modele_a_voir = st.selectbox("Modèles existants", list(modeles.keys()), key="profil_modele_select")
            m = modeles[modele_a_voir]
            codes_assoc = [c.strip() for c in m.get("codes_ape","").strip().split("\n") if c.strip()]
            if codes_assoc:
                st.caption(f"🏭 Codes APE associés : {', '.join(codes_assoc)}")
            else:
                st.caption("🏭 Aucun code APE associé")
            col_a, col_b = st.columns(2)
            with col_b:
                if st.button("🗑️ Supprimer ce modèle", key="delete_modele"):
                    del modeles[modele_a_voir]
                    sauvegarder_modeles(p["email"], modeles)
                    st.success(f"Modèle supprimé !")
                    st.rerun()
            with col_a:
                if st.button("✏️ Modifier les codes APE", key="edit_ape_modele"):
                    st.session_state["edit_modele"] = modele_a_voir
            if st.session_state.get("edit_modele") == modele_a_voir:
                new_codes = st.text_area("Nouveaux codes APE", value=m.get("codes_ape",""), height=100, key="edit_ape_input")
                if st.button("💾 Mettre à jour", key="update_ape_modele"):
                    modeles[modele_a_voir]["codes_ape"] = new_codes
                    sauvegarder_modeles(p["email"], modeles)
                    st.session_state.profil_connecte["modeles_email"] = modeles
                    st.session_state.pop("edit_modele", None)
                    st.success("✅ Codes APE mis à jour !")
                    st.rerun()

        with st.expander("➕ Créer un nouveau modèle"):
            nouveau_nom = st.text_input("Nom du modèle", placeholder="Ex: BTP, Espaces verts...", key="nouveau_modele_nom")
            nouveau_sujet = st.text_input("Sujet", value="Demande de stage d'immersion – {nom_entreprise}", key="nouveau_modele_sujet")
            nouveau_corps = st.text_area("Corps", value="Madame, Monsieur,\n\n{prenom_nom}", height=180, key="nouveau_modele_corps")
            nouveau_codes_ape = st.text_area("🏭 Codes APE associés (un par ligne)", placeholder="43.31Z\n43.99C", height=100, key="nouveau_modele_ape")
            if st.button("💾 Sauvegarder ce modèle", key="save_modele"):
                if not nouveau_nom:
                    st.error("Donne un nom à ce modèle !")
                else:
                    modeles[nouveau_nom] = {"sujet": nouveau_sujet, "corps": nouveau_corps, "codes_ape": nouveau_codes_ape}
                    sauvegarder_modeles(p["email"], modeles)
                    st.session_state.profil_connecte["modeles_email"] = modeles
                    st.success(f"✅ Modèle '{nouveau_nom}' sauvegardé !")
                    st.rerun()

        st.markdown("#### 🔗 Associer un CV à des codes APE")
        st.caption("L'outil choisira automatiquement le bon CV selon le code APE de l'entreprise.")
        profil_frais = charger_profil(p["email"])
        cv_sauvegardes_profil = profil_frais.get("cv_noms", [])
        associations_ape = profil_frais.get("associations_ape_cv", {})
        st.session_state.profil_connecte["cv_noms"] = cv_sauvegardes_profil
        st.session_state.profil_connecte["associations_ape_cv"] = associations_ape

        if not cv_sauvegardes_profil:
            st.info("Aucun CV sauvegardé. Va dans l'onglet 📧 Emails pour uploader et sauvegarder un CV.")
        else:
            nouvelles_associations = {}
            for cv_nom in cv_sauvegardes_profil:
                codes_actuels = associations_ape.get(cv_nom, "")
                codes_input = st.text_area(f"📄 {cv_nom}", value=codes_actuels, placeholder="43.31Z\n43.99C", height=100, key=f"ape_cv_{cv_nom}")
                nouvelles_associations[cv_nom] = codes_input
            if st.button("💾 Sauvegarder les associations", key="save_ape_cv"):
                profil_data = charger_profil(p["email"])
                profil_data["associations_ape_cv"] = nouvelles_associations
                sauvegarder_profil(p["email"], profil_data)
                st.session_state.profil_connecte["associations_ape_cv"] = nouvelles_associations
                st.success("✅ Associations sauvegardées !")

        st.markdown("#### 🔔 Relances automatiques")
        p_relance_auto = st.toggle("Activer les relances automatiques", value=p.get("relance_auto", False))
        if p_relance_auto:
            col1, col2 = st.columns(2)
            with col1:
                p_relance_delai = st.number_input("⏳ Relancer après (jours)", min_value=1, max_value=30, value=int(p.get("relance_delai", 7)))
            with col2:
                p_relance_nb_max = st.number_input("🔁 Nombre max de relances", min_value=1, max_value=5, value=int(p.get("relance_nb_max", 1)))
            p_sujet_relance = st.text_input("Sujet relance", value=p.get("sujet_relance", SUJET_RELANCE_DEFAULT), key="profil_sujet_relance")
            p_corps_relance = st.text_area("Corps relance", value=p.get("corps_relance", CORPS_RELANCE_DEFAULT), height=200, key="profil_corps_relance")
        else:
            p_relance_delai = int(p.get("relance_delai", 7))
            p_relance_nb_max = int(p.get("relance_nb_max", 1))
            p_sujet_relance = p.get("sujet_relance", SUJET_RELANCE_DEFAULT)
            p_corps_relance = p.get("corps_relance", CORPS_RELANCE_DEFAULT)

        if st.button("💾 Sauvegarder mes paramètres", type="primary"):
            donnees = {
                "nom": p_nom, "situation": p_situation, "adresse": p_adresse,
                "rayon": p_rayon, "codes_ape": p_codes_ape,
                "min_sal": p_min_sal, "max_sal": p_max_sal, "max_entreprises": p_max_entreprises,
                "sujet": p_sujet, "corps": p_corps,
                "relance_auto": p_relance_auto, "relance_delai": p_relance_delai,
                "relance_nb_max": p_relance_nb_max, "sujet_relance": p_sujet_relance,
                "corps_relance": p_corps_relance,
                "cv_noms": cv_sauvegardes_profil,
                "associations_ape_cv": associations_ape,
                "modeles_email": charger_modeles(p["email"]),
            }
            sauvegarder_profil(p["email"], donnees)
            st.session_state.profil_connecte.update(donnees)
            st.success("✅ Paramètres sauvegardés !")

        st.markdown("---")
        st.subheader("📬 Historique")
        historique = charger_historique(p["email"])
        if not historique:
            st.write("Aucune entreprise contactée pour l'instant.")
        else:
            import pandas as pd
            recherche_hist = st.text_input("🔍 Rechercher dans l'historique", placeholder="Nom, ville...", key="search_historique")
            hist_filtre = {k: v for k, v in historique.items() if not recherche_hist or recherche_hist.lower() in v.get("nom","").lower() or recherche_hist.lower() in v.get("ville","").lower()}
            df_hist = pd.DataFrame([{
                "⭐": "⭐" if v.get("favori") else "", "Nom": v["nom"], "Ville": v["ville"],
                "Email": v["email"], "Date contact": v["date_contact"],
                "Statut": v.get("statut_kanban",""), "Relances": v.get("nb_relances",0),
                "Répondu": "✅" if v.get("repondu") else "❌"
            } for v in hist_filtre.values()])
            st.caption(f"{len(hist_filtre)} résultat(s) sur {len(historique)}")
            st.dataframe(df_hist, use_container_width=True, height=300)
            if st.button("🗑️ Réinitialiser l'historique", type="secondary"):
                sauvegarder_historique(p["email"], {})
                st.success("Historique réinitialisé !")
                st.rerun()

        st.markdown("---")
        st.subheader("🗂️ Sauvegarde & Restauration")
        col_exp, col_imp = st.columns(2)
        with col_exp:
            st.markdown("**📤 Exporter mes données**")
            if st.button("📤 Exporter", key="export_btn"):
                export_data = {
                    "profil": charger_profil(p["email"]),
                    "historique": charger_historique(p["email"]),
                    "email": p["email"],
                    "date_export": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.download_button(
                    label="⬇️ Télécharger la sauvegarde",
                    data=json.dumps(export_data, ensure_ascii=False, indent=2),
                    file_name=f"sauvegarde_stage_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json", key="download_export"
                )
        with col_imp:
            st.markdown("**📥 Importer une sauvegarde**")
            import_file = st.file_uploader("Fichier .json", type=["json"], key="import_file")
            if import_file:
                if st.button("📥 Restaurer", key="import_btn"):
                    try:
                        import_data = json.loads(import_file.read().decode("utf-8"))
                        if "profil" in import_data and "historique" in import_data:
                            sauvegarder_profil(p["email"], import_data["profil"])
                            sauvegarder_historique(p["email"], import_data["historique"])
                            st.session_state.profil_connecte.update(import_data["profil"])
                            st.success(f"✅ {len(import_data['historique'])} entreprises importées !")
                            st.rerun()
                        else:
                            st.error("Fichier invalide.")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

# ══════════════════════════════════════════════════════════════════
# TAB 2 — RECHERCHE
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.header("🔍 Rechercher des entreprises")
    if not st.session_state.profil_connecte:
        st.warning("⚠️ Connecte-toi d'abord dans l'onglet 👤 Profil.")
    else:
        p = st.session_state.profil_connecte
        col1, col2 = st.columns(2)
        with col1:
            adresse = st.text_input("📍 Adresse de référence", value=p.get("adresse",""), placeholder="Richebourg, 62", key="recherche_adresse")
            rayon = st.slider("📏 Rayon (km)", min_value=1, max_value=100, value=int(p.get("rayon", 20)))
        with col2:
            codes_ape_input = st.text_area("🏭 Codes APE/NAF (un par ligne)", value=p.get("codes_ape",""), height=120, key="recherche_codes_ape")
            max_results = st.number_input("Nombre max d'entreprises", min_value=10, max_value=500, value=int(p.get("max_entreprises", 100)))

        st.markdown("#### 👥 Filtre salariés")
        col3, col4 = st.columns(2)
        with col3:
            min_sal = st.number_input("Minimum", min_value=0, max_value=10000, value=int(p.get("min_sal", 1)), key="recherche_min_sal")
        with col4:
            max_sal = st.number_input("Maximum", min_value=1, max_value=10000, value=int(p.get("max_sal", 50)), key="recherche_max_sal")

        if st.button("🚀 Lancer la recherche", type="primary"):
            if not adresse or not codes_ape_input:
                st.error("Remplis l'adresse et au moins un code APE !")
            elif min_sal > max_sal:
                st.error("Le minimum ne peut pas être supérieur au maximum !")
            else:
                codes = [c for c in codes_ape_input.strip().split("\n") if c.strip()]
                with st.spinner("📍 Géolocalisation..."):
                    coords = geocode_adresse(adresse)
                if not coords:
                    st.error("Adresse introuvable.")
                else:
                    with st.spinner("🔎 Recherche en cours..."):
                        resultats = rechercher_entreprises(codes, coords, rayon, max_results, min_sal, max_sal, p["email"])
                    st.session_state.entreprises = resultats
                    nb_n = sum(1 for e in resultats if not e["deja_contactee"])
                    nb_d = sum(1 for e in resultats if e["deja_contactee"])
                    st.success(f"✅ {len(resultats)} entreprises — **{nb_n} nouvelles** / {nb_d} déjà contactées")

                    with st.spinner("🌐 Recherche automatique des sites, emails et téléphones..."):
                        progress_auto = st.progress(0)
                        stats = {"site": 0, "pj": 0, "fb": 0, "email": 0, "tel": 0}
                        for i, e in enumerate(st.session_state.entreprises):
                            if not e.get("site_web"):
                                # 1. Tentative directe de domaine
                                site = chercher_site_tentative_directe(e["nom"], e["ville"])
                                if site:
                                    e["site_web"] = site
                                    stats["site"] += 1

                            if not e.get("site_web"):
                                # 2. Certificats SSL via crt.sh
                                delai_humain(0.5, 1.5)
                                site = chercher_crt_sh(e["nom"])
                                if site:
                                    e["site_web"] = site
                                    stats["site"] += 1

                            if not e.get("site_web"):
                                # 3. Google Maps
                                site = chercher_site_google(e["nom"], e["ville"])
                                if site:
                                    e["site_web"] = site
                                    stats["site"] += 1

                            if not e.get("site_web"):
                                # 4. Pages Jaunes
                                pj = chercher_pages_jaunes(e["nom"], e["ville"])
                                if pj:
                                    e["pages_jaunes"] = pj
                                    stats["pj"] += 1

                            if not e.get("facebook"):
                                # 5. Facebook
                                fb = chercher_facebook(e["nom"], e["ville"])
                                if fb:
                                    e["facebook"] = fb
                                    stats["fb"] += 1

                            # 6. Verif.com via SIREN
                            if not e.get("site_web"):
                                try:
                                    siren = e.get("siren", "")
                                    site_v, em_v, tel_v = chercher_verif_com(siren)
                                    if site_v and not e["site_web"]:
                                        e["site_web"] = site_v
                                        stats["site"] += 1
                                except Exception: pass

                            # 7. Societe.ninja via SIREN
                            if not e.get("site_web"):
                                try:
                                    siren = e.get("siren", "")
                                    site_sn, em_sn, tel_sn = chercher_societe_ninja(siren)
                                    if site_sn and not e["site_web"]:
                                        e["site_web"] = site_sn
                                        stats["site"] += 1
                                except Exception: pass

                            # 8. LinkedIn entreprise
                            if not e.get("linkedin"):
                                try:
                                    lk = chercher_linkedin_entreprise(e["nom"], e["ville"])
                                    if lk:
                                        e["linkedin"] = lk
                                        stats["site"] += 1
                                except Exception: pass

                            sources = [e.get("site_web"), e.get("pages_jaunes"), e.get("facebook")]
                            for src in sources:
                                if src:
                                    em, tel = extraire_contact_site(src)
                                    if em and not e["email"]:
                                        e["email"] = em
                                        stats["email"] += 1
                                    if tel and not e["telephone"]:
                                        e["telephone"] = tel
                                        stats["tel"] += 1
                                if e["email"] and e["telephone"]:
                                    break
                            if e["deja_contactee"]:
                                hist = charger_historique(p["email"])
                                cle = e["nom"].strip().lower()
                                if cle in hist:
                                    hist[cle].update({"site_web": e.get("site_web",""), "pages_jaunes": e.get("pages_jaunes",""), "facebook": e.get("facebook",""), "email": e.get("email",""), "telephone": e.get("telephone","")})
                                    sauvegarder_historique(p["email"], hist)
                            progress_auto.progress((i + 1) / max(len(st.session_state.entreprises), 1))
                            delai_humain(1.0, 3.0)  # Délai humain entre chaque entreprise
                        st.success(f"🌐 Sites : **{stats['site']}** | 📒 Pages Jaunes : **{stats['pj']}** | 📘 Facebook : **{stats['fb']}** | 📧 Emails : **{stats['email']}** | 📞 Tél : **{stats['tel']}**")

        if st.session_state.entreprises:
            st.markdown("---")
            import pandas as pd
            col_f, col_d = st.columns(2)
            afficher_deja = col_d.checkbox("Afficher les déjà contactées", value=True)
            only_favoris = col_f.checkbox("⭐ Favoris uniquement", value=False)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🕵️ Chercher emails + téléphones (manuel)"):
                    progress = st.progress(0)
                    for i, e in enumerate(st.session_state.entreprises):
                        for src in [e.get("site_web"), e.get("pages_jaunes"), e.get("facebook")]:
                            if src:
                                em, tel = extraire_contact_site(src)
                                if em and not e["email"]: e["email"] = em
                                if tel and not e["telephone"]: e["telephone"] = tel
                            if e["email"] and e["telephone"]: break
                        progress.progress((i + 1) / len(st.session_state.entreprises))
                    st.success("Recherche de contacts terminée !")

            liste = st.session_state.entreprises
            if not afficher_deja:
                liste = [e for e in liste if not e["deja_contactee"]]
            if only_favoris:
                liste = [e for e in liste if e["favori"]]

            recherche_nom = st.text_input("🔍 Filtrer les résultats", placeholder="Nom, ville...", key="search_resultats")
            if recherche_nom:
                liste = [e for e in liste if recherche_nom.lower() in e["nom"].lower() or recherche_nom.lower() in e["ville"].lower()]
            st.caption(f"{len(liste)} entreprise(s) affichée(s)")

            df = pd.DataFrame([{
                "⭐": "⭐" if e["favori"] else "", "Nom": e["nom"], "Ville": e["ville"],
                "APE": e["code_ape"], "Dist. (km)": e["distance_km"],
                "Effectif": e.get("effectif_approx","?"), "Email": e["email"],
                "Téléphone": e["telephone"], "Statut": e.get("statut_kanban",""),
                "Contactée": "✅" if e["deja_contactee"] else "🆕",
            } for e in liste])
            st.dataframe(df, use_container_width=True, height=400)

            st.markdown("---")
            st.subheader("📇 Fiche entreprise")
            noms = [e["nom"] for e in st.session_state.entreprises]
            selected = st.selectbox("Choisir une entreprise", noms, key="select_modif")
            e_sel = next((e for e in st.session_state.entreprises if e["nom"] == selected), None)
            if e_sel:
                favori_icon = "⭐ " if e_sel.get("favori") else ""
                site_lien = f'<a href="{e_sel["site_web"]}" target="_blank">🌐 Voir</a>' if e_sel.get("site_web") else "🌐 Non trouvé"
                pj_lien = f'<a href="{e_sel["pages_jaunes"]}" target="_blank">📒 Voir</a>' if e_sel.get("pages_jaunes") else "📒 Non trouvé"
                fb_lien = f'<a href="{e_sel["facebook"]}" target="_blank">📘 Voir</a>' if e_sel.get("facebook") else "📘 Non trouvé"
                st.markdown(f"""
<div style="background:#1e1e3a;border-radius:12px;padding:20px;border-left:5px solid #4a90d9;margin-bottom:16px;">
<h3 style="margin:0 0 12px 0;color:#7eb8f7;">{favori_icon}{e_sel['nom']}</h3>
<table style="width:100%;border-collapse:collapse;color:#e2e8f0;">
<tr><td style="padding:4px 8px;color:#a0aec0;">📍 Adresse</td><td>{e_sel.get('adresse','Non renseignée')}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">🏙️ Ville</td><td>{e_sel.get('ville','')}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">🏭 Code APE</td><td>{e_sel.get('code_ape','')}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">👥 Effectif</td><td>~{e_sel.get('effectif_approx','?')} salariés</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">📏 Distance</td><td>{e_sel.get('distance_km','?')} km</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">📧 Email</td><td>{e_sel.get('email','Non trouvé') or 'Non trouvé'}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">📞 Téléphone</td><td>{e_sel.get('telephone','Non trouvé') or 'Non trouvé'}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">🌐 Site web</td><td>{site_lien}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">📒 Pages Jaunes</td><td>{pj_lien}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">📘 Facebook</td><td>{fb_lien}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">📋 Statut</td><td>{e_sel.get('statut_kanban','')}</td></tr>
<tr><td style="padding:4px 8px;color:#a0aec0;">📅 Contactée le</td><td>{e_sel.get('date_contact','Jamais') or 'Jamais'}</td></tr>
</table>
</div>""", unsafe_allow_html=True)
                with st.expander("✏️ Modifier cette fiche"):
                    col1, col2 = st.columns(2)
                    with col1:
                        fav = st.checkbox("⭐ Favori", value=e_sel.get("favori", False), key="modif_favori")
                        statut = st.selectbox("Statut Kanban", COLONNES_KANBAN,
                            index=COLONNES_KANBAN.index(e_sel.get("statut_kanban", COLONNES_KANBAN[0])) if e_sel.get("statut_kanban") in COLONNES_KANBAN else 0,
                            key="modif_statut")
                    with col2:
                        email_modif = st.text_input("📧 Email", value=e_sel.get("email",""), key="modif_email")
                        tel_modif = st.text_input("📞 Téléphone", value=e_sel.get("telephone",""), key="modif_tel")
                    col3, col4 = st.columns(2)
                    with col3:
                        site_modif = st.text_input("🌐 Site web", value=e_sel.get("site_web",""), key="modif_site")
                    with col4:
                        pj_modif = st.text_input("📒 Pages Jaunes", value=e_sel.get("pages_jaunes",""), key="modif_pj")
                    fb_modif = st.text_input("📘 Facebook", value=e_sel.get("facebook",""), key="modif_fb")
                    note = st.text_area("📝 Ajouter une note", value="", placeholder="Note horodatée...", key="modif_note", height=80)
                    if st.button("💾 Enregistrer les modifications"):
                        for e in st.session_state.entreprises:
                            if e["nom"] == selected:
                                e.update({"favori": fav, "statut_kanban": statut, "email": email_modif,
                                          "telephone": tel_modif, "site_web": site_modif,
                                          "pages_jaunes": pj_modif, "facebook": fb_modif})
                        hist = charger_historique(p["email"])
                        cle = selected.strip().lower()
                        if cle in hist:
                            hist[cle].update({"favori": fav, "statut_kanban": statut, "email": email_modif,
                                              "telephone": tel_modif, "site_web": site_modif,
                                              "pages_jaunes": pj_modif, "facebook": fb_modif})
                            if note:
                                hist[cle]["notes"] = (hist[cle].get("notes","") + f"\n[{datetime.now().strftime('%d/%m/%Y')}] {note}").strip()
                            sauvegarder_historique(p["email"], hist)
                        st.success("✅ Modifications enregistrées !")
                        st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 3 — KANBAN
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.header("📋 Tableau Kanban")
    if not st.session_state.profil_connecte:
        st.warning("⚠️ Connecte-toi d'abord dans l'onglet 👤 Profil.")
    else:
        p = st.session_state.profil_connecte
        historique = charger_historique(p["email"])
        if not historique:
            st.info("Aucune entreprise dans l'historique.")
        else:
            col_refresh, col_info = st.columns([1, 3])
            with col_refresh:
                auto_refresh = st.toggle("🔄 Actualisation auto (30s)", value=False, key="kanban_auto_refresh")
            if auto_refresh:
                st.markdown('<script>setTimeout(function(){window.location.reload();},30000);</script>', unsafe_allow_html=True)
            cols = st.columns(len(COLONNES_KANBAN))
            for i, col_name in enumerate(COLONNES_KANBAN):
                with cols[i]:
                    entreprises_col = [v for v in historique.values() if v.get("statut_kanban","📤 Contactée") == col_name]
                    auto_label = " 🔄" if i < 3 and auto_refresh else ""
                    st.markdown(f"**{col_name}{auto_label}** ({len(entreprises_col)})")
                    st.markdown("---")
                    for e in entreprises_col:
                        favori_icon = "⭐ " if e.get("favori") else ""
                        st.markdown(f"""<div style="background:#1e1e3a;border-radius:8px;padding:10px;margin-bottom:8px;border-left:4px solid #4a90d9;">
<b style="color:#e2e8f0;">{favori_icon}{e['nom']}</b><br>
<small style="color:#a0aec0;">📍 {e['ville']}</small><br>
<small style="color:#a0aec0;">📅 {e.get('date_contact','')}</small><br>
<small style="color:#a0aec0;">🔁 {e.get('nb_relances',0)} relance(s)</small>
</div>""", unsafe_allow_html=True)
                        nouveau_statut = st.selectbox("Déplacer vers", COLONNES_KANBAN,
                            index=COLONNES_KANBAN.index(col_name), key=f"kanban_{e['nom'][:20]}")
                        if nouveau_statut != col_name:
                            cle = e["nom"].strip().lower()
                            historique[cle]["statut_kanban"] = nouveau_statut
                            if nouveau_statut == "📬 Réponse reçue":
                                historique[cle]["repondu"] = True
                            sauvegarder_historique(p["email"], historique)
                            st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 4 — EMAILS
# ══════════════════════════════════════════════════════════════════
with tab4:
    st.header("📧 Envoi automatique des emails")
    if not st.session_state.profil_connecte:
        st.warning("⚠️ Connecte-toi d'abord dans l'onglet 👤 Profil.")
    else:
        p = st.session_state.profil_connecte
        st.success(f"✅ Connecté : **{p['email']}**")

        with st.expander("📖 Comment créer un mot de passe d'application Gmail ?"):
            st.markdown("""
1. Va sur [myaccount.google.com](https://myaccount.google.com)
2. **Sécurité** → **Validation en deux étapes**
3. **Mots de passe des applications** → crée un mot de passe "Mail" → copie le code 16 caractères
            """)

        col1, col2 = st.columns(2)
        with col1:
            ton_nom = st.text_input("👤 Prénom et nom", value=p.get("nom",""), key="email_nom")
        with col2:
            ta_formation = st.text_input("🎓 Situation", value=p.get("situation",""), key="email_situation")

        st.markdown("---")
        st.subheader("📎 CV")
        profil_frais_cv = charger_profil(p["email"])
        cv_sauvegardes = profil_frais_cv.get("cv_noms", [])

        col_cv1, col_cv2 = st.columns(2)
        with col_cv1:
            cv_file = st.file_uploader("Ajouter / remplacer un CV (PDF)", type=["pdf"], key="cv_uploader")
            if cv_file:
                cv_label = st.text_input("Nom pour ce CV", placeholder="Ex: CV BTP, CV Espaces verts", key="cv_label_input")
                if st.button("💾 Sauvegarder ce CV", key="save_cv_btn"):
                    if not cv_label:
                        st.error("Donne un nom à ce CV !")
                    else:
                        chemin = f"cv_{get_profil_id(p['email'])}_{cv_label.replace(' ','_')}.pdf"
                        with open(chemin, "wb") as f_cv:
                            f_cv.write(cv_file.read())
                        profil_data = charger_profil(p["email"])
                        cv_liste = profil_data.get("cv_noms", [])
                        if cv_label not in cv_liste:
                            cv_liste.append(cv_label)
                        profil_data["cv_noms"] = cv_liste
                        sauvegarder_profil(p["email"], profil_data)
                        st.session_state.profil_connecte["cv_noms"] = cv_liste
                        st.success(f"✅ CV '{cv_label}' sauvegardé !")
                        st.rerun()
        with col_cv2:
            if cv_sauvegardes:
                cv_choisi_label = st.selectbox("📂 Choisir un CV sauvegardé", cv_sauvegardes, key="cv_select")
                chemin_cv_sauvegarde = f"cv_{get_profil_id(p['email'])}_{cv_choisi_label.replace(' ','_')}.pdf"
                if os.path.exists(chemin_cv_sauvegarde):
                    st.success(f"✅ CV sélectionné : **{cv_choisi_label}**")
                else:
                    st.warning("Ce CV n'existe plus sur le disque.")
                    chemin_cv_sauvegarde = None
                if st.button("🗑️ Supprimer ce CV", key="delete_cv_btn"):
                    if chemin_cv_sauvegarde and os.path.exists(chemin_cv_sauvegarde):
                        os.remove(chemin_cv_sauvegarde)
                    cv_sauvegardes.remove(cv_choisi_label)
                    profil_data = charger_profil(p["email"])
                    profil_data["cv_noms"] = cv_sauvegardes
                    sauvegarder_profil(p["email"], profil_data)
                    st.session_state.profil_connecte["cv_noms"] = cv_sauvegardes
                    st.rerun()
            else:
                st.info("Aucun CV sauvegardé.")
                chemin_cv_sauvegarde = None

        st.markdown("---")
        modeles_dispo = charger_modeles(p["email"])
        if modeles_dispo:
            col_mod1, col_mod2 = st.columns([2, 1])
            with col_mod1:
                modele_choisi = st.selectbox("📚 Utiliser un modèle", ["-- Modèle par défaut --"] + list(modeles_dispo.keys()), key="email_modele_select")
            with col_mod2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📥 Charger", key="load_modele"):
                    if modele_choisi != "-- Modèle par défaut --":
                        st.session_state["email_sujet_val"] = modeles_dispo[modele_choisi]["sujet"]
                        st.session_state["email_corps_val"] = modeles_dispo[modele_choisi]["corps"]
                        st.rerun()

        sujet_val = st.session_state.get("email_sujet_val", p.get("sujet","Demande de stage d'immersion – {nom_entreprise}"))
        corps_val = st.session_state.get("email_corps_val", p.get("corps",""))
        sujet = st.text_input("Sujet", value=sujet_val, key="email_sujet")
        corps = st.text_area("Corps", value=corps_val, height=280, key="email_corps")

        if p.get("relance_auto"):
            st.info(f"🔔 Relances auto activées : après **{p.get('relance_delai',7)} jours**, max **{p.get('relance_nb_max',1)} fois**.")

        st.markdown("---")
        if not st.session_state.entreprises:
            st.warning("⚠️ Lance d'abord une recherche dans l'onglet 🔍 Recherche")
        else:
            a_contacter = [e for e in st.session_state.entreprises if e["email"] and not e["deja_contactee"]]
            sans_email = [e for e in st.session_state.entreprises if not e["email"] and not e["deja_contactee"]]
            deja = [e for e in st.session_state.entreprises if e["deja_contactee"]]
            col1, col2, col3 = st.columns(3)
            col1.metric("🆕 Prêtes à envoyer", len(a_contacter))
            col2.metric("❌ Sans email", len(sans_email))
            col3.metric("✅ Déjà contactées", len(deja))

            if st.button("📤 Envoyer les emails", type="primary"):
                if not ton_nom:
                    st.error("Remplis ton prénom et nom !")
                elif not a_contacter:
                    st.warning("Aucune nouvelle entreprise avec un email.")
                else:
                    chemin_cv_temp = None
                    if cv_file:
                        chemin_cv_temp = f"cv_temp_{cv_file.name}"
                        with open(chemin_cv_temp, "wb") as f_tmp:
                            f_tmp.write(cv_file.read())

                    associations_ape_cv = charger_profil(p["email"]).get("associations_ape_cv", {})
                    modeles_send = charger_modeles(p["email"])

                    def get_cv_pour_entreprise(code_ape):
                        for cv_nom, codes_str in associations_ape_cv.items():
                            codes = [c.strip().upper() for c in codes_str.strip().split("\n") if c.strip()]
                            if code_ape.upper() in codes:
                                chemin = f"cv_{get_profil_id(p['email'])}_{cv_nom.replace(' ','_')}.pdf"
                                if os.path.exists(chemin):
                                    return chemin, cv_nom
                        if chemin_cv_sauvegarde and os.path.exists(chemin_cv_sauvegarde):
                            return chemin_cv_sauvegarde, cv_choisi_label
                        if chemin_cv_temp:
                            return chemin_cv_temp, "CV temporaire"
                        return None, None

                    def get_modele_pour_entreprise(code_ape):
                        for modele_nom, modele_data in modeles_send.items():
                            codes = [c.strip().upper() for c in modele_data.get("codes_ape","").strip().split("\n") if c.strip()]
                            if code_ape.upper() in codes:
                                return modele_data["sujet"], modele_data["corps"], modele_nom
                        return sujet, corps, "Modèle par défaut"

                    progress = st.progress(0)
                    succes_list, echecs = [], 0
                    cv_utilises, modeles_utilises = {}, {}

                    for i, e in enumerate(a_contacter):
                        sujet_auto, corps_auto, nom_modele = get_modele_pour_entreprise(e.get("code_ape",""))
                        corps_p = corps_auto.replace("{nom_entreprise}", e["nom"]).replace("{ville}", e["ville"])
                        corps_p = corps_p.replace("{prenom_nom}", ton_nom).replace("{formation}", ta_formation)
                        sujet_p = sujet_auto.replace("{nom_entreprise}", e["nom"])
                        chemin_cv, nom_cv = get_cv_pour_entreprise(e.get("code_ape",""))
                        cv_utilises[nom_cv or "Aucun"] = cv_utilises.get(nom_cv or "Aucun", 0) + 1
                        modeles_utilises[nom_modele] = modeles_utilises.get(nom_modele, 0) + 1
                        result = envoyer_email(p["email"], p["mdp"], e["email"], sujet_p, corps_p, chemin_cv)
                        if result is True:
                            succes_list.append(e)
                        else:
                            echecs += 1
                        progress.progress((i + 1) / len(a_contacter))
                        time.sleep(1)

                    if succes_list:
                        marquer_contactees(p["email"], succes_list)
                        for e in st.session_state.entreprises:
                            if e in succes_list:
                                e["deja_contactee"] = True
                                e["date_contact"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                                e["statut_kanban"] = "📤 Contactée"

                    if chemin_cv_temp and os.path.exists(chemin_cv_temp):
                        os.remove(chemin_cv_temp)

                    st.success(f"✅ {len(succes_list)} emails envoyés !")
                    if echecs:
                        st.warning(f"⚠️ {echecs} échecs.")
                    if cv_utilises:
                        st.info("📄 CVs : " + " | ".join([f"**{k}** : {v}" for k, v in cv_utilises.items()]))
                    if modeles_utilises:
                        st.info("✉️ Modèles : " + " | ".join([f"**{k}** : {v}" for k, v in modeles_utilises.items()]))

# ══════════════════════════════════════════════════════════════════
# TAB 5 — CARTE
# ══════════════════════════════════════════════════════════════════
with tab5:
    st.header("🗺️ Carte des entreprises")
    if not st.session_state.entreprises:
        st.warning("⚠️ Lance d'abord une recherche.")
    else:
        try:
            import folium
            from streamlit_folium import st_folium
            liste = st.session_state.entreprises
            coords_valides = [e for e in liste if e.get("lat") and e.get("lon")]
            if not coords_valides:
                st.warning("Aucune coordonnée disponible.")
            else:
                center_lat = sum(e["lat"] for e in coords_valides) / len(coords_valides)
                center_lon = sum(e["lon"] for e in coords_valides) / len(coords_valides)
                m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
                for e in coords_valides:
                    color = "gold" if e.get("favori") else ("green" if e.get("deja_contactee") else "blue")
                    icon = "star" if e.get("favori") else ("check" if e.get("deja_contactee") else "info-sign")
                    popup_html = f"<b>{e['nom']}</b><br>📍 {e['ville']}<br>📏 {e['distance_km']} km<br>📧 {e['email'] or 'Pas d\'email'}<br>📞 {e['telephone'] or 'Pas de téléphone'}"
                    folium.Marker(location=[e["lat"], e["lon"]], popup=folium.Popup(popup_html, max_width=250),
                        tooltip=e["nom"], icon=folium.Icon(color=color, icon=icon, prefix="glyphicon")).add_to(m)
                st.caption("🔵 Nouvelle  🟢 Déjà contactée  🟡 Favori")
                st_folium(m, width=None, height=550, use_container_width=True)
        except ImportError:
            st.info("Pour activer la carte, tape dans le terminal :")
            st.code("pip install folium streamlit-folium")

# ══════════════════════════════════════════════════════════════════
# TAB 6 — STATISTIQUES
# ══════════════════════════════════════════════════════════════════
with tab6:
    st.header("📈 Tableau de bord")
    if not st.session_state.profil_connecte:
        st.warning("⚠️ Connecte-toi d'abord dans l'onglet 👤 Profil.")
    else:
        p = st.session_state.profil_connecte
        historique = charger_historique(p["email"])
        if not historique:
            st.info("Aucune donnée disponible.")
        else:
            import pandas as pd
            total = len(historique)
            repondus = sum(1 for e in historique.values() if e.get("repondu"))
            favoris = sum(1 for e in historique.values() if e.get("favori"))
            entretiens = sum(1 for e in historique.values() if e.get("statut_kanban") == "🤝 Entretien")
            acceptes = sum(1 for e in historique.values() if e.get("statut_kanban") == "✅ Accepté")
            relances_total = sum(e.get("nb_relances", 0) for e in historique.values())
            taux_reponse = round(repondus / total * 100, 1) if total > 0 else 0

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📤 Emails envoyés", total)
            col2.metric("📬 Réponses", repondus, f"{taux_reponse}%")
            col3.metric("🤝 Entretiens", entretiens)
            col4.metric("✅ Acceptés", acceptes)
            col5, col6, col7 = st.columns(3)
            col5.metric("⭐ Favoris", favoris)
            col6.metric("🔁 Relances", relances_total)
            col7.metric("📊 Taux réponse", f"{taux_reponse}%")

            st.markdown("---")
            st.subheader("📊 Répartition par statut")
            statuts = {}
            for e in historique.values():
                s = e.get("statut_kanban","📤 Contactée")
                statuts[s] = statuts.get(s, 0) + 1
            st.bar_chart(pd.DataFrame(list(statuts.items()), columns=["Statut","Nombre"]).set_index("Statut"))

            st.subheader("🏙️ Top villes")
            villes = {}
            for e in historique.values():
                v = e.get("ville","Inconnue")
                villes[v] = villes.get(v, 0) + 1
            df_villes = pd.DataFrame(list(villes.items()), columns=["Ville","Nombre"]).sort_values("Nombre", ascending=False).head(10)
            st.bar_chart(df_villes.set_index("Ville"))

# ══════════════════════════════════════════════════════════════════
# TAB 7 — EXPORT EXCEL
# ══════════════════════════════════════════════════════════════════
with tab7:
    st.header("📊 Export Excel")
    if not st.session_state.entreprises:
        st.warning("⚠️ Lance d'abord une recherche dans l'onglet 🔍 Recherche")
    else:
        nb_n = sum(1 for e in st.session_state.entreprises if not e["deja_contactee"])
        nb_d = sum(1 for e in st.session_state.entreprises if e["deja_contactee"])
        nb_f = sum(1 for e in st.session_state.entreprises if e["favori"])
        col1, col2, col3 = st.columns(3)
        col1.metric("🆕 Nouvelles", nb_n)
        col2.metric("✅ Déjà contactées", nb_d)
        col3.metric("⭐ Favoris", nb_f)
        st.caption("Les favoris sont en jaune, les déjà contactées en gris dans le fichier.")
        filepath = "candidatures_stage.xlsx"
        if st.button("📥 Générer le fichier Excel", type="primary"):
            generer_excel(st.session_state.entreprises, filepath)
            with open(filepath, "rb") as f:
                st.download_button(
                    label="⬇️ Télécharger candidatures_stage.xlsx",
                    data=f,
                    file_name="candidatures_stage.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.success("✅ Fichier Excel généré !")
