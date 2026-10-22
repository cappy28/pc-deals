import threading
import time

from flask import Flask, redirect, render_template, request, url_for

import collector
import config
import db

app = Flask(__name__)
ITEMS = {i["nom"]: i for i in config.WATCHLIST}


def boucle():
    while True:
        collector.collecter()
        time.sleep(config.INTERVALLE_MINUTES * 60)


def meilleure_offre(nom, mediane):
    for o in db.offres_composant(nom, jours=7):
        if collector.evaluer(o["prix"], ITEMS[nom]["prix_max"], mediane) != "suspect":
            return o
    return None


@app.route("/")
def index():
    f_type = request.args.get("type", "")
    f_source = request.args.get("source", "")
    f_affaires = request.args.get("affaires") == "1"
    medianes = {nom: db.mediane(nom) for nom in ITEMS}

    resume, total, manquants = [], 0, []
    for nom in config.MA_CONFIG:
        item = ITEMS.get(nom)
        if not item:
            continue
        m = meilleure_offre(nom, medianes[nom])
        if m:
            total += m["prix"]
        else:
            manquants.append(nom)
        resume.append({"nom": nom, "type": item["type"], "prix_max": item["prix_max"],
                       "mediane": medianes[nom], "meilleure": m})

    lignes = []
    for o in db.offres(f_type or None, f_source or None):
        item = ITEMS.get(o["composant"])
        if not item:
            continue
        statut = collector.evaluer(o["prix"], item["prix_max"], medianes.get(o["composant"]))
        if f_affaires and statut != "affaire":
            continue
        lignes.append({**o, "statut": statut})

    return render_template("index.html", etat=collector.etat, resume=resume, total=total,
                           manquants=manquants, lignes=lignes,
                           types=sorted({i["type"] for i in config.WATCHLIST}),
                           f_type=f_type, f_source=f_source, f_affaires=f_affaires)


@app.route("/collecter", methods=["POST"])
def lancer():
    threading.Thread(target=collector.collecter, daemon=True).start()
    return redirect(url_for("index"))


if __name__ == "__main__":
    db.init()
    threading.Thread(target=boucle, daemon=True).start()
    print("➡️  Ouvre http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
  
