# AI Talent Network publication

This repository publishes an existing standalone demo to GitHub Pages.

- `index.html` is generated from `src/template.html`, `data/talent.json`, and independent role evidence in `data/current_roles_verified.json`.
- Run `python3 build_page.py` after edits. `sync_page.py` imports bibliographic data from an external HTML snapshot while preserving this repository's template and role evidence.
- Keep current institution, position, project tier, and historical discovery affiliation separate. Never promote an old note or a lack of search results into a verified current appointment.
- Current role assertions need a source URL, check date, and explicit evidence status. Unknown or conflicting positions stay unknown. Project tiers do not establish official titles, age, career stage, or recruiting suitability.
- Preserve search, filters, researcher details, shortlist controls, copy actions, and verification notes.
- Do not change names, affiliations, scores, or verification claims as part of a hosting change.
- Never commit credentials, local environments, crawler caches, private correspondence, or machine-specific configuration.
- Preview the page and check the live GitHub Pages deployment after publishing. A successful push alone is not deployment verification.
- Scope future changes to the user's request. Do not send the site to anyone without authorization.
