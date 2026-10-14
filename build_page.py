"""Build the standalone page from the local template, dataset, and role evidence."""

import argparse
import copy
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "src" / "template.html"
DATA_PATH = ROOT / "data" / "talent.json"
ROLES_PATH = ROOT / "data" / "current_roles_verified.json"
OUTPUT_PATH = ROOT / "index.html"


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
    return clean


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


def prepare_page(data=None):
    if data is None:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    roles = json.loads(ROLES_PATH.read_text(encoding="utf-8")) if ROLES_PATH.exists() else {}
    merged = merge_roles(data, roles)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count("__DATA__") != 1:
        raise ValueError("Template must contain exactly one __DATA__ placeholder")
    for anchor in ("roster", "shortlist", "method"):
        if not re.search(rf'\bid=[\"\']{anchor}[\"\']', template):
            raise ValueError(f"Template is missing the {anchor} section")
    blob = json.dumps(merged, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return template.replace("__DATA__", blob), merged


def build(data=None, output=OUTPUT_PATH):
    html, merged = prepare_page(data)
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
