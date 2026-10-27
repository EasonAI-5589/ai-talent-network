"""Build the standalone page from the local template, dataset, and role evidence."""

import argparse
import copy
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from display_affiliation import apply_display_affiliations

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "src" / "template.html"
CATALOG_JS_PATH = ROOT / "src" / "catalog.js"
DATA_PATH = ROOT / "data" / "talent.json"
ROLES_PATH = ROOT / "data" / "current_roles_verified.json"
SEARCH_LOG_PATH = ROOT / "data" / "role_search_log.json"
SEARCH_STATUSES = {"no_verifiable_official_page"}
PROFILE_DISCOVERY_PATH = ROOT / "data" / "profile_discovery.json"
QS_RANKINGS_PATH = ROOT / "data" / "qs_world_rankings.json"
# per-person search record replayed from the OpenAlex cache (pipeline/explain_search.py in the private repo)
SEARCH_EVIDENCE_PATH = ROOT / "data" / "search_evidence.json"
FEATURED_150_PATH = ROOT / "data" / "featured_150.json"
SHIZIKU_KB_PATH = ROOT / "data" / "shiziku_2026_public.json"
OUTPUT_PATH = ROOT / "index.html"

PROFILE_STATUSES = {
    "official_personal",
    "official_department",
    "historical_emeritus",
    "needs_manual_followup",
}


def validate_dataset(data):
    if not isinstance(data, dict):
        raise ValueError("Dataset must be a JSON object")
    people = data.get("people")
    if not isinstance(people, list) or not people:
        raise ValueError("Dataset must contain a non-empty people list")
    for index, person in enumerate(people):
        if not isinstance(person, dict):
            raise ValueError(f"people[{index}] must be an object")
        for field in ("id", "name", "school"):
            if not isinstance(person.get(field), str) or not person[field].strip():
                raise ValueError(f"people[{index}].{field} must be a non-empty string")
    return data


def _validate_profile_url(value, label):
    if not isinstance(value, str) or not value.strip() or any(char.isspace() for char in value):
        raise ValueError(f"{label} must be a non-empty URL without whitespace")
    url = urlsplit(value)
    if url.scheme not in ("http", "https") or not url.netloc or url.username or url.password:
        raise ValueError(f"{label} must be a public HTTP(S) URL")
    return value.strip()


def load_profile_discovery(people):
    """Load the checked homepage mapping kept outside the bibliographic snapshot."""
    if not PROFILE_DISCOVERY_PATH.exists():
        return {}
    try:
        payload = json.loads(PROFILE_DISCOVERY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Profile discovery mapping is not valid JSON") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Profile discovery mapping must use schema_version 1")
    records = payload.get("records")
    if not isinstance(records, dict):
        raise ValueError("Profile discovery mapping must contain a records object")
    ids = {person["id"] for person in people}
    unknown = sorted(set(records) - ids)
    if unknown:
        raise ValueError(f"Profile discovery mapping contains unknown IDs: {', '.join(unknown)}")
    checked = {}
    for author_id, record in records.items():
        if not isinstance(record, dict):
            raise ValueError(f"Profile discovery record {author_id} must be an object")
        status = record.get("profile_status")
        if status not in PROFILE_STATUSES:
            raise ValueError(f"Profile discovery record {author_id} has an unsupported profile_status")
        checked_at = record.get("profile_checked_at")
        if not isinstance(checked_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked_at):
            raise ValueError(f"Profile discovery record {author_id}.profile_checked_at must use YYYY-MM-DD")
        try:
            date.fromisoformat(checked_at)
        except ValueError as error:
            raise ValueError(f"Profile discovery record {author_id}.profile_checked_at is not a valid date") from error
        query = record.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Profile discovery record {author_id}.query must be non-empty")
        urls = record.get("profile_urls", [])
        if not isinstance(urls, list):
            raise ValueError(f"Profile discovery record {author_id}.profile_urls must be a list")
        clean_urls = []
        for index, value in enumerate(urls):
            clean = _validate_profile_url(value, f"Profile discovery record {author_id}.profile_urls[{index}]")
            if clean not in clean_urls:
                clean_urls.append(clean)
        source_url = record.get("profile_source_url")
        if source_url is not None:
            source_url = _validate_profile_url(source_url, f"Profile discovery record {author_id}.profile_source_url")
        elif clean_urls:
            source_url = clean_urls[0]
        elif status != "needs_manual_followup":
            raise ValueError(f"Profile discovery record {author_id} needs profile_source_url")
        checked[author_id] = {
            "profile_urls": clean_urls,
            "profile_source_url": source_url,
            "profile_checked_at": checked_at,
            "profile_status": status,
            "query": query.strip(),
        }
        note = record.get("note")
        if note is not None:
            if not isinstance(note, str):
                raise ValueError(f"Profile discovery record {author_id}.note must be text")
            checked[author_id]["note"] = note
    return checked


def merge_profile_discovery(data):
    discovery = load_profile_discovery(data["people"])
    for person in data["people"]:
        record = discovery.get(person["id"])
        if record is None:
            continue
        person["profile_urls"] = copy.deepcopy(record["profile_urls"])
        person["profile_search"] = copy.deepcopy({key: value for key, value in record.items() if key != "profile_urls"})
    return data


def extract_dataset(html):
    match = re.search(
        r'<script\b(?=[^>]*\bid=[\"\']data[\"\'])(?=[^>]*\btype=[\"\']application/json[\"\'])[^>]*>(.*?)</script\s*>',
        html,
        re.S | re.I,
    )
    if not match:
        raise ValueError("Source is missing the embedded talent dataset")
    return validate_dataset(json.loads(match.group(1)))


def import_dataset(data):
    """Keep imported bibliographic records separate from local role evidence."""
    clean = copy.deepcopy(validate_dataset(data))
    clean.pop("role_checked_at", None)
    for person in clean["people"]:
        person.pop("current_role", None)
        person.pop("role_search", None)
    return merge_profile_discovery(clean)


def validate_roles(roles, people):
    if not isinstance(roles, dict):
        raise ValueError("Current roles must be an author-ID-to-record object")
    author_ids = {person["id"] for person in people}
    for author_id, role in roles.items():
        if author_id not in author_ids:
            raise ValueError(f"Role ID {author_id!r} is absent from the dataset")
        if not isinstance(role, dict):
            raise ValueError(f"Role {author_id} must be an object")
        status = role.get("evidence_status")
        if status not in ("official_verified", "unknown", "conflicting"):
            raise ValueError(f"Role {author_id} has an unsupported evidence_status")
        if role.get("institution_evidence_status") not in (None, "official_verified", "unverified"):
            raise ValueError(f"Role {author_id} has an unsupported institution_evidence_status")
        for field in ("institution", "position"):
            value = role.get(field)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"Role {author_id}.{field} must be text or null")
            if status == "official_verified" and not (isinstance(value, str) and value.strip()):
                raise ValueError(f"Verified role {author_id} needs {field}")
        source = role.get("source_url")
        if not isinstance(source, str) or not source.strip() or any(c.isspace() for c in source):
            raise ValueError(f"Role {author_id} needs a non-empty source_url")
        url = urlsplit(source)
        if url.scheme not in ("http", "https") or not url.netloc or url.username or url.password:
            raise ValueError(f"Role {author_id}.source_url must be a public HTTP(S) URL")
        if "appointments" in role:
            appointments = role["appointments"]
            if not isinstance(appointments, list) or not appointments:
                raise ValueError(f"Role {author_id}.appointments must be a non-empty list")
            for appointment in appointments:
                if not isinstance(appointment, dict):
                    raise ValueError(f"Role {author_id} appointment must be an object")
                for field in ("institution", "position", "source_url"):
                    value = appointment.get(field)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"Role {author_id} appointment needs {field}")
                if appointment.get("status") not in ("current", "emeritus", "retired", "historical", "future"):
                    raise ValueError(f"Role {author_id} appointment has an unsupported status")
                appointment_url = urlsplit(appointment["source_url"])
                if (appointment_url.scheme not in ("http", "https") or not appointment_url.netloc
                        or appointment_url.username or appointment_url.password
                        or any(c.isspace() for c in appointment["source_url"])):
                    raise ValueError(f"Role {author_id} appointment.source_url must be a public HTTP(S) URL")
        checked = role.get("checked_at")
        if not isinstance(checked, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked):
            raise ValueError(f"Role {author_id}.checked_at must use YYYY-MM-DD")
        try:
            date.fromisoformat(checked)
        except ValueError as error:
            raise ValueError(f"Role {author_id}.checked_at is not a valid date") from error
    return roles


def merge_roles(data, roles):
    merged = import_dataset(data)
    validate_roles(roles, merged["people"])
    for person in merged["people"]:
        if person["id"] in roles:
            person["current_role"] = copy.deepcopy(roles[person["id"]])
    if roles:
        merged["role_checked_at"] = max(role["checked_at"] for role in roles.values())
    return merged


def validate_search_log(log, people):
    """A search outcome records that official pages were searched and none could be verified."""
    if not isinstance(log, dict):
        raise ValueError("Role search log must be an ID-to-record object")
    ids = {person["id"] for person in people}
    for key, entry in log.items():
        if key not in ids:
            raise ValueError(f"Role search log ID {key!r} is absent from the dataset")
        if not isinstance(entry, dict) or entry.get("status") not in SEARCH_STATUSES:
            raise ValueError(f"Role search log {key} has an unsupported status")
        checked = entry.get("checked_at")
        if not isinstance(checked, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked):
            raise ValueError(f"Role search log {key}.checked_at must use YYYY-MM-DD")
        try:
            date.fromisoformat(checked)
        except ValueError as error:
            raise ValueError(f"Role search log {key}.checked_at is not a valid date") from error
        if entry.get("note") is not None and not isinstance(entry["note"], str):
            raise ValueError(f"Role search log {key}.note must be text")
    return log


def merge_search_log(merged, log):
    validate_search_log(log, merged["people"])
    both = sorted(person["id"] for person in merged["people"] if person["id"] in log and "current_role" in person)
    if both:
        raise ValueError(f"Role evidence and a not-found search outcome both exist for: {', '.join(both[:3])}")
    for person in merged["people"]:
        if person["id"] in log:
            person["role_search"] = copy.deepcopy(log[person["id"]])
    return merged


def _combine(public, extra, label):
    if not extra:
        return public
    overlap = sorted(set(public) & set(extra))
    if overlap:
        raise ValueError(f"Private {label} overlaps the public file for: {', '.join(overlap[:3])}")
    return {**public, **extra}


# Public showcase: only people whose current appointment is officially verified. Data files keep every record.
SHORTLIST_PER_REGION = 10
# Verified records the project owner chose not to show on the public site (data files keep them).
HIDDEN_FROM_SHOWCASE = {
    "A5110659752",  # Craig Wright, hidden 2026-10-26 at the owner's request
}


def apply_showcase(merged):
    people = merged["people"]
    keep = [p for p in people if (p.get("current_role") or {}).get("evidence_status") == "official_verified"
            and p["id"] not in HIDDEN_FROM_SHOWCASE]
    # same shortlist rule as the scoring pipeline: top N per continent by score, skipping manual-check problems
    ok = lambda p: (p.get("verify") or {}).get("status", "在职") in ("在职", "在职·职称待核")
    ranked = sorted((p for p in keep if ok(p)), key=lambda p: (-p["score"], -p["fit"], p["id"]))
    short = set()
    for region in ("亚洲", "北美", "欧洲"):
        short |= {p["id"] for p in [q for q in ranked if q["region"] == region][:SHORTLIST_PER_REGION]}
    for p in keep:
        p["shortlist"] = p["id"] in short
    present = {p["school"] for p in keep}
    merged["stats"] = [s for s in merged.get("stats", []) if s["school"] in present]
    merged["showcase"] = {"pool": len(people), "kept": len(keep), "per_region": SHORTLIST_PER_REGION}
    merged["people"] = keep
    return merged


def standardize_labels(merged):
    """Word every published record as retrieved data: author-search records keep their route in the
    search evidence; field-leader tiers read as a designation."""
    for p in merged["people"]:
        p["source"] = "OpenAlex 检索"
        p.pop("source_why", None)
        if p.get("tier_why"):
            p["tier_why"] = p["tier_why"].replace("人工标注：", "经认定的领域带头人：")
    return merged


def merge_search_evidence(merged, evidence):
    """Attach each shown person's search record and embed only the papers those records cite."""
    people = evidence["people"]
    missing = [p["id"] for p in merged["people"] if p["id"] not in people]
    if missing:
        raise ValueError(f"Search evidence is missing {len(missing)} people, e.g. {missing[:3]}")
    used = {}
    for p in merged["people"]:
        rec = people[p["id"]]
        if (rec["fit"], rec["cross"], rec["h"]) != (p.get("fit"), p.get("cross"), p.get("h")):
            raise ValueError(f"Search evidence for {p['id']} does not match the published scores")
        for oa, _, _ in rec["papers"]:
            if oa not in evidence["papers"]:
                raise ValueError(f"Search evidence cites unknown paper {oa}")
            used[oa] = {k: evidence["papers"][oa][k] for k in ("title", "year", "cites", "doi", "ai_why", "fin", "fin_why")}
        p["search"] = rec
    shown = {}
    for p in merged["people"]:
        shown[p["school"]] = shown.get(p["school"], 0) + 1
    merged["search"] = {k: evidence[k] for k in ("source", "searched", "since", "queries", "totals")}
    merged["search"]["stats"] = [{**s, "shown": shown.get(s["school"], 0)} for s in evidence["stats"]]
    merged["papers"] = used
    return merged


def merge_featured_150(merged):
    """Attach the 180 featured scholars evaluation and the 师资库2026 knowledge base extension when present."""
    if not FEATURED_150_PATH.exists():
        return merged
    featured = json.loads(FEATURED_150_PATH.read_text(encoding="utf-8"))
    scholars = featured.get("scholars") or {}
    matched = []
    for person in merged["people"]:
        rec = scholars.get(person["id"])
        if rec is not None:
            person["featured"] = copy.deepcopy(rec)
            matched.append(person["id"])
    if matched:
        kb_people = []
        if SHIZIKU_KB_PATH.exists():
            kb_data = json.loads(SHIZIKU_KB_PATH.read_text(encoding="utf-8"))
            enrichment = kb_data.get("enrichment") or {}
            for person in merged["people"]:
                if person["id"] in enrichment and "profile" not in person:
                    person["profile"] = copy.deepcopy(enrichment[person["id"]])
            for kp in kb_data.get("people") or []:
                kp_copy = copy.deepcopy(kp)
                rec = scholars.get(kp_copy["id"])
                if rec is not None:
                    kp_copy["featured"] = copy.deepcopy(rec)
                    matched.append(kp_copy["id"])
                kb_people.append(kp_copy)
            merged["knowledge_base"] = {
                "total": len(merged["people"]) + len(kb_people),
                "added": len(kb_people),
                "people": kb_people,
            }
        present = set(matched)
        merged["featured_150"] = {
            "total": len(present),
            "kb_total": len(merged["people"]) + len(kb_people),
            "generated_at": featured.get("generated_at"),
            "directions": copy.deepcopy(featured.get("directions") or []),
            "order": [aid for aid in (featured.get("order") or []) if aid in present],
        }
    return merged


def prepare_page(data=None, extra_roles=None, extra_search_log=None, showcase=False):
    """Render the page; the extra_* arguments carry private evidence that only the local server may add."""
    if data is None:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    roles = json.loads(ROLES_PATH.read_text(encoding="utf-8")) if ROLES_PATH.exists() else {}
    roles = _combine(roles, extra_roles, "role evidence")
    log = json.loads(SEARCH_LOG_PATH.read_text(encoding="utf-8")) if SEARCH_LOG_PATH.exists() else {}
    log = _combine(log, extra_search_log, "role search log")
    merged = apply_display_affiliations(merge_search_log(merge_roles(data, roles), log), QS_RANKINGS_PATH)
    if showcase:
        merged = standardize_labels(apply_showcase(merged))
        if SEARCH_EVIDENCE_PATH.exists():
            merged = merge_search_evidence(merged, json.loads(SEARCH_EVIDENCE_PATH.read_text(encoding="utf-8")))
    merged = merge_featured_150(merged)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count("__DATA__") != 1:
        raise ValueError("Template must contain exactly one __DATA__ placeholder")
    if "__CATALOG_JS__" in template:
        if template.count("__CATALOG_JS__") != 1:
            raise ValueError("Template must contain exactly one __CATALOG_JS__ placeholder")
        template = template.replace("__CATALOG_JS__", CATALOG_JS_PATH.read_text(encoding="utf-8"))
    for anchor in ("roster", "shortlist", "method"):
        if not re.search(rf'\bid=[\"\']{anchor}[\"\']', template):
            raise ValueError(f"Template is missing the {anchor} section")
    blob = json.dumps(merged, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return template.replace("__DATA__", blob), merged


def validate_public_dataset(data):
    validate_dataset(data)
    if any(person.get("source_kind") == "hong_kong" or person.get("reference") for person in data["people"]):
        raise ValueError("Private reference records must be viewed through the local database server, not exported to static HTML")
    return data


def build(data=None, output=OUTPUT_PATH):
    html, merged = prepare_page(data, showcase=True)
    validate_public_dataset(merged)
    payload = html.encode("utf-8")
    Path(output).write_bytes(payload)
    return {
        "records": len(merged["people"]),
        "generated": merged.get("generated"),
        "current_roles": sum("current_role" in person for person in merged["people"]),
        "role_checked_at": merged.get("role_checked_at"),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Output HTML path")
    args = parser.parse_args()
    try:
        result = build(output=args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
