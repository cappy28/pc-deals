import random
import re
import time
import xml.etree.ElementTree as ET

import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
DEALABS_RSS = "https://www.dealabs.com/rss/groupe/informatique"


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


def dealabs():
    """Promos neuves depuis le flux RSS informatique de Dealabs."""
    r = httpx.get(DEALABS_RSS, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for item in root.iter("item"):
        titre = (item.findtext("title") or "").strip()
        lien = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or lien).strip()
        prix, marchand = None, ""
        for el in item:  # balise <pepper:merchant name="..." price="..."/>
            if el.tag.endswith("merchant"):
                marchand = el.get("name", "")
                prix = parse_prix(el.get("price"))
        if prix is None:
            m = re.search(r"(\d[\d\s.,]*)\s?€", titre)
            prix = parse_prix(m.group(1)) if m else None
        out.append({"source": "dealabs", "ext_id": guid, "titre": titre,
                    "prix": prix, "url": lien, "lieu": marchand or "Neuf (promo)"})
    return out


def leboncoin(recherches):
    """recherches = [(texte, prix_min, prix_max), ...] -> (offres, erreur)"""
    try:
        import lbc
    except ImportError:
        return [], "librairie 'lbc' non installée"

    client = lbc.Client()
    out = []
    for texte, pmin, pmax in recherches:
        try:
            res = client.search(text=texte, page=1, limit=35,
                                sort=lbc.Sort.NEWEST, price=[pmin, pmax])
        except Exception as e:
            return out, f"bloqué/erreur sur '{texte}' : {e}"
        for ad in res.ads:
            prix = ad.price[0] if isinstance(ad.price, list) and ad.price else ad.price
            lieu = getattr(getattr(ad, "location", None), "city", "") or ""
            out.append({"source": "leboncoin", "ext_id": str(ad.id), "titre": ad.subject or "",
                        "prix": parse_prix(prix), "url": ad.url, "lieu": lieu})
        time.sleep(random.uniform(4, 9))  # rester discret
    return out, None
  
