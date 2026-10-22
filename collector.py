import re
import threading
import unicodedata
from datetime import datetime

import httpx

import config
import db
import sources

_verrou = threading.Lock()
etat = {"quand": None, "nouvelles": 0, "erreurs": []}


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


def telegram(msg):
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        return
    try:
        httpx.post(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                   data={"chat_id": config.TELEGRAM_CHAT_ID, "text": msg,
                         "disable_web_page_preview": "true"}, timeout=15)
    except Exception as e:
        print("[telegram]", e)


def collecter():
    if not _verrou.acquire(blocking=False):
        return  # une collecte tourne déjà
    try:
        premier_passage = db.nombre() == 0  # pas de spam au tout premier lancement
        brutes, erreurs = [], []

        try:
            brutes += sources.dealabs()
        except Exception as e:
            erreurs.append(f"Dealabs : {e}")

        recherches = [(i.get("recherche", i["nom"]), int(i["prix_max"] * 0.4), int(i["prix_max"] * 1.4))
                      for i in config.WATCHLIST]
        lbc_offres, err = sources.leboncoin(recherches)
        brutes += lbc_offres
        if err:
            erreurs.append(f"Leboncoin : {err}")

        nouvelles = 0
        for o in brutes:
            item = trouver_composant(o["titre"])
            if not item:
                continue
            o.update(composant=item["nom"], type=item["type"],
                     vu_le=datetime.now().isoformat(timespec="seconds"))
            if not db.ajouter(o):
                continue
            nouvelles += 1
            statut = evaluer(o["prix"], item["prix_max"], db.mediane(item["nom"]))
            if not premier_passage and statut in ("affaire", "suspect"):
                icone = "🔥" if statut == "affaire" else "⚠️ SUSPECT"
                telegram(f"{icone} {item['nom']} — {o['prix']:.0f} € ({o['source']})\n{o['titre']}\n{o['url']}")

        etat.update(quand=datetime.now().strftime("%d/%m %H:%M"), nouvelles=nouvelles, erreurs=erreurs)
        print(f"[collecte] {nouvelles} nouvelle(s) offre(s) — erreurs : {erreurs or 'aucune'}")
    finally:
        _verrou.release()
  
