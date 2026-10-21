"""Choose one institution for presentation while preserving appointment evidence."""

import copy
from datetime import date
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
DEFAULT_RANKING_PATH = ROOT / "data" / "qs_world_rankings.json"
CUHK = "香港中文大学"
CUHK_EN = "The Chinese University of Hong Kong"
CUHK_SHENZHEN = "香港中文大学（深圳）"
CUHK_SHENZHEN_EN = "The Chinese University of Hong Kong, Shenzhen"


def _key(value):
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", value or "").casefold())


CUHK_NAMES = {_key(name) for name in (CUHK, CUHK_EN, "Chinese University of Hong Kong", "CUHK", "港中大")}
SHENZHEN_NAMES = {_key(name) for name in (
    "香港中文大学（深圳）", "香港中文大学深圳", "The Chinese University of Hong Kong, Shenzhen",
    "Chinese University of Hong Kong Shenzhen", "CUHK-Shenzhen", "CUHK(SZ)", "CUHKSZ", "港中深",
)}


def _public_url(value):
    if not isinstance(value, str) or not value.strip() or any(c.isspace() for c in value):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc) and not parsed.username and not parsed.password


def _load_rankings(path):
    with Path(path).open(encoding="utf-8") as source:
        ranking = json.load(source)
    if not isinstance(ranking, dict) or not isinstance(ranking.get("institutions"), list):
        raise ValueError("QS rankings must contain an institutions list")
    edition = ranking.get("edition")
    if type(edition) is not int or edition < 1:
        raise ValueError("QS rankings need an edition year")
    checked = ranking.get("checked_at")
    if not isinstance(checked, str):
        raise ValueError("QS rankings need checked_at")
    try:
        date.fromisoformat(checked)
    except ValueError as error:
        raise ValueError("QS rankings checked_at must be an ISO date") from error
    if not _public_url(ranking.get("source_url")):
        raise ValueError("QS rankings need a public source_url")
    aliases = {}
    for institution in ranking["institutions"]:
        if not isinstance(institution, dict) or not isinstance(institution.get("institution"), str) or not institution["institution"].strip():
            raise ValueError("QS institution needs an institution name")
        rank = institution.get("rank")
        if rank is not None and (type(rank) is not int or rank < 1):
            raise ValueError("QS rank must be a positive integer or null")
        names = institution.get("aliases", [])
        if not isinstance(names, list) or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("QS institution aliases must be a list of names")
        english = institution.get("institution_en")
        if english is not None and not isinstance(english, str):
            raise ValueError("QS institution_en must be text")
        for name in [institution["institution"], english, *names]:
            if not name:
                continue
            key = _key(name)
            previous = aliases.get(key)
            if previous and previous["institution"] != institution["institution"]:
                raise ValueError(f"QS alias {name!r} identifies multiple institutions")
            aliases[key] = institution
    return aliases


def _canonical(appointment, aliases):
    names = [appointment.get("institution"), appointment.get("institution_en")]
    keys = [_key(name) for name in names if name]
    is_shenzhen = any(key in SHENZHEN_NAMES for key in keys)
    if is_shenzhen:
        ranked = next((aliases[key] for key in keys if key in aliases and _key(aliases[key]["institution"]) in SHENZHEN_NAMES), {})
        return {"institution": CUHK_SHENZHEN, "institution_en": CUHK_SHENZHEN_EN,
                "rank": ranked.get("rank"), "group": "cuhk-shenzhen"}
    if any(key in CUHK_NAMES for key in keys):
        ranked = next((aliases[key] for key in CUHK_NAMES if key in aliases), {})
        return {"institution": CUHK, "institution_en": CUHK_EN, "rank": ranked.get("rank"),
                "group": "cuhk"}
    ranked = next((aliases[key] for key in keys if key in aliases), None)
    if ranked:
        return {"institution": ranked["institution"], "institution_en": ranked.get("institution_en") or appointment.get("institution_en"),
                "rank": ranked.get("rank"), "group": "cuhk" if _key(ranked["institution"]) in CUHK_NAMES else _key(ranked["institution"])}
    return {"institution": appointment["institution"], "institution_en": appointment.get("institution_en"),
            "rank": None, "group": _key(appointment["institution"])}


def _candidate(appointment, aliases, *, selected_evidence=False):
    if (not isinstance(appointment, dict) or not isinstance(appointment.get("institution"), str)
            or not appointment["institution"].strip() or not _public_url(appointment.get("source_url"))):
        return None
    return {"appointment": appointment, "canonical": _canonical(appointment, aliases), "selected_evidence": selected_evidence}


def _candidates(role, aliases):
    verified = role.get("evidence_status") == "official_verified"
    known = bool(role.get("institution")) and (verified or role.get("institution_evidence_status") == "official_verified")
    raw = role.get("appointments") or []
    result = []
    if known:
        for appointment in raw:
            if appointment.get("status") in ("current", "emeritus"):
                candidate = _candidate(appointment, aliases)
                if candidate:
                    result.append(candidate)
        if not result and raw:
            for appointment in raw:
                if appointment.get("status") == "retired":
                    candidate = _candidate(appointment, aliases)
                    if candidate:
                        result.append(candidate)
        if not raw and not re.search(r"[;；|]", role["institution"]):
            position = role.get("position") or ""
            status = "retired" if re.search(r"retired|退休", position, re.I) else "emeritus" if re.search(r"emerit|荣休", position, re.I) else "current"
            candidate = _candidate({"institution": role["institution"], "institution_en": role.get("institution_en"),
                "position": role.get("position") if verified else None, "department": role.get("department"),
                "source_url": role.get("source_url"), "checked_at": role.get("checked_at"), "status": status}, aliases)
            if candidate:
                result.append(candidate)
    for appointment in role.get("selection_candidates") or []:
        if appointment.get("evidence_status") == "official_verified" and appointment.get("status") == "current":
            candidate = _candidate(appointment, aliases, selected_evidence=True)
            if candidate:
                result.append(candidate)
    return result


def _unique(values):
    return list(dict.fromkeys(value for value in values if value))


def _display_role(role, aliases):
    candidates = _candidates(role, aliases)
    if not candidates:
        return None
    if {"cuhk", "cuhk-shenzhen"}.issubset({c["canonical"]["group"] for c in candidates}):
        hong_kong = next(c["canonical"] for c in candidates if c["canonical"]["group"] == "cuhk")
        for candidate in candidates:
            if candidate["canonical"]["group"] == "cuhk-shenzhen":
                candidate["canonical"].update(institution=CUHK, institution_en=CUHK_EN, rank=hong_kong["rank"])
    order = {"current": 0, "emeritus": 1, "retired": 2}
    # Rank always takes precedence; equal ranks preserve institution order. A
    # canonical institution's active campus post takes precedence over emeritus.
    first_institution = {}
    for index, candidate in enumerate(candidates):
        first_institution.setdefault(candidate["canonical"]["institution"], index)
    chosen = min(candidates, key=lambda c: (
        c["canonical"]["rank"] if c["canonical"]["rank"] is not None else float("inf"),
        first_institution[c["canonical"]["institution"]], order[c["appointment"]["status"]],
    ))
    first = chosen["appointment"]
    selected = [c for c in candidates if c["canonical"]["group"] == chosen["canonical"]["group"]
                and c["appointment"]["status"] == first["status"]]
    appointments = [copy.deepcopy(c["appointment"]) for c in selected]
    position = None
    if role.get("evidence_status") == "official_verified" or all(c["selected_evidence"] for c in selected):
        positions = _unique(a.get("position") for a in appointments)
        position = "；".join(positions) or None
        if position and first["status"] == "retired" and not re.search(r"retired|退休", position, re.I):
            position += "（退休教职）"
    return {
        "institution": chosen["canonical"]["institution"],
        "institution_en": chosen["canonical"]["institution_en"],
        "position": position,
        "department": "；".join(_unique(a.get("department") for a in appointments)) or None,
        "source_url": first["source_url"],
        "source_urls": _unique(a["source_url"] for a in appointments),
        "checked_at": first.get("checked_at") or role.get("checked_at"),
        "status": first["status"],
        "source_institution": first["institution"],
        "appointments": appointments,
    }


def apply_display_affiliations(dataset, ranking_path=DEFAULT_RANKING_PATH):
    """Return a deep copy with one display_role per supported appointment record.

    Ranking chooses presentation only. current_role, its evidence status, every
    appointment, and the reference row are retained unchanged.
    """
    aliases = _load_rankings(ranking_path)
    result = copy.deepcopy(dataset)
    for person in result.get("people", []):
        person.pop("display_role", None)
        role = person.get("current_role")
        if isinstance(role, dict):
            display = _display_role(role, aliases)
            if display:
                person["display_role"] = display
    return result
