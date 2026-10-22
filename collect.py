import json
import os
import random
import re
import statistics
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

import config

FICHIER = Path(__file__).parent / "docs" / "data.json"
TZ = ZoneInfo("Europe/Paris")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def maintenant(delta_jours=0):
    d = datetime.now(TZ).replace(tzinfo=None) - timedelta(days=delta_jours)
    return d.isoformat(timespec="seconds")


# ---------------------------------------------------------------- utilitaires
def parse_prix(s):
    """'1 299,99€' -> 1299.99 ; '499.99' -> 499.99 ; '1.299' -> 1299"""
    if s is None:
        return None
    s = str(s).replace("\xa0", "").replace("\u202f", "").replace(" ", "").replace("€", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+\.\d{3}", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def normaliser(t):
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def contient(texte_norm, mot):
    mot_n = normaliser(mot)
    if len(mot_n.replace(" ", "")) <= 3:          # mots courts ("ti", "hs") : mot entier
        return f" {mot_n} " in f" {texte_norm} "
    return mot_n.replace(" ", "") in texte_norm.replace(" ", "")


def trouver_composant(titre):
    t = normaliser(titre)
    if any(contient(t, x) for x in config.EXCLUSIONS_GLOBALES):
        return None
    for item in config.WATCHLIST:
        if all(contient(t, m) for m in item["mots"]) and \
           not any(contient(t, x) for x in item.get("exclure", [])):
            return item
    return None


def evaluer(prix, prix_max, mediane=None):
    if prix is None:
        return "inconnu"
    if prix < prix_max * 0.35 or (mediane and prix < mediane * 0.5):
        return "suspect"
    if prix <= prix_max:
        return "affaire"
    return "normal"


# ---------------------------------------------------------------- sources
def dealabs():
    out = []
    for flux in config.DEALABS_FLUX:
        r = httpx.get(flux, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        r.raise_for_status()
        for item in ET.fromstring(r.content).iter("item"):
            titre = (item.findtext("title") or "").strip()
            lien = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or lien).strip()
            prix, marchand = None, ""
            for el in item:  # <pepper:merchant name="..." price="..."/>
                if el.tag.endswith("merchant"):
                    marchand = el.get("name", "")
                    prix = parse_prix(el.get("price"))
            if prix is None:
                m = re.search(r"(\d[\d\s.,]*)\s?€", titre)
                prix = parse_prix(m.group(1)) if m else None
            out.append({"source": "dealabs", "ext_id": guid, "titre": titre,
                        "prix": prix, "url": lien, "lieu": marchand or "Neuf (promo)"})
    return out


def leboncoin():
    try:
        import lbc
    except ImportError:
        return [], "librairie 'lbc' non installée"
    client = lbc.Client()
    out = []
    for item in config.WATCHLIST:
        texte = item.get("recherche", item["nom"])
        pmin, pmax = int(item["prix_max"] * 0.4), int(item["prix_max"] * 1.4)
        try:
            res = client.search(text=texte, page=1, limit=35,
                                sort=lbc.Sort.NEWEST, price=[pmin, pmax])
        except Exception as e:
            return out, f"bloqué/erreur sur '{texte}' : {str(e)[:150]}"
        for ad in res.ads:
            prix = ad.price[0] if isinstance(ad.price, list) and ad.price else ad.price
            lieu = getattr(getattr(ad, "location", None), "city", "") or ""
            out.append({"source": "leboncoin", "ext_id": str(ad.id), "titre": ad.subject or "",
                        "prix": parse_prix(prix), "url": ad.url, "lieu": lieu})
        time.sleep(random.uniform(3, 6))
    return out, None


def telegram(msg):
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return
    try:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                   data={"chat_id": chat, "text": msg, "disable_web_page_preview": "true"},
                   timeout=15)
    except Exception as e:
        print("[telegram]", e)


# ---------------------------------------------------------------- principal
def main():
    items = {i["nom"]: i for i in config.WATCHLIST}
    ancien = json.loads(FICHIER.read_text("utf-8")) if FICHIER.exists() else {}
    premier_passage = not ancien.get("offres")
    limite = maintenant(config.JOURS_HISTORIQUE)

    offres = {f'{o["source"]}:{o["ext_id"]}': o for o in ancien.get("offres", [])
              if o["vu_le"] >= limite and o["composant"] in items}

    brutes, erreurs = [], []
    try:
        brutes += dealabs()
    except Exception as e:
        erreurs.append(f"Dealabs : {str(e)[:150]}")
    if config.LEBONCOIN_ACTIF:
        lbc_offres, err = leboncoin()
        brutes += lbc_offres
        if err:
            erreurs.append(f"Leboncoin : {err}")

    nouvelles = []
    for o in brutes:
        item = trouver_composant(o["titre"])
        cle = f'{o["source"]}:{o["ext_id"]}'
        if not item or o["prix"] is None or cle in offres or not str(o["url"]).startswith("http"):
            continue
        o.update(composant=item["nom"], type=item["type"], vu_le=maintenant())
        offres[cle] = o
        nouvelles.append(o)

    # Prix médian d'occasion par composant
    medianes = {}
    for nom in items:
        prix = [o["prix"] for o in offres.values() if o["composant"] == nom and o["source"] == "leboncoin"]
        medianes[nom] = statistics.median(prix) if len(prix) >= 3 else None
    for o in offres.values():
        o["statut"] = evaluer(o["prix"], items[o["composant"]]["prix_max"], medianes[o["composant"]])

    # Notifications Telegram
    if not premier_passage:
        for o in nouvelles:
            if o["statut"] in ("affaire", "suspect"):
                icone = "🔥" if o["statut"] == "affaire" else "⚠️ SUSPECT"
                telegram(f"{icone} {o['composant']} — {o['prix']:.0f} € ({o['source']})\n{o['titre']}\n{o['url']}")

    # Ma config : meilleure offre non suspecte des 7 derniers jours
    limite7 = maintenant(7)
    resume, total, manquants = [], 0, []
    for nom in config.MA_CONFIG:
        if nom not in items:
            continue
        candidates = [o for o in offres.values() if o["composant"] == nom
                      and o["vu_le"] >= limite7 and o["statut"] != "suspect"]
        best = min(candidates, key=lambda o: o["prix"]) if candidates else None
        if best:
            total += best["prix"]
        else:
            manquants.append(nom)
        resume.append({"nom": nom, "type": items[nom]["type"], "prix_max": items[nom]["prix_max"],
                       "mediane": medianes[nom], "meilleure": best})

    sortie = {
        "maj": maintenant()[:16].replace("T", " "),
        "nouvelles": len(nouvelles),
        "erreurs": erreurs,
        "types": sorted({i["type"] for i in config.WATCHLIST}),
        "config": resume, "total": total, "manquants": manquants,
        "offres": sorted(offres.values(), key=lambda o: o["vu_le"], reverse=True),
    }
    FICHIER.parent.mkdir(exist_ok=True)
    FICHIER.write_text(json.dumps(sortie, ensure_ascii=False, indent=1), "utf-8")
    print(f"{len(nouvelles)} nouvelle(s) offre(s) — erreurs : {erreurs or 'aucune'}")


if __name__ == "__main__":
    main()
  
