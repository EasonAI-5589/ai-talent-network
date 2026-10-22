# PBCSF AI Talent Dashboard

An interactive pilot directory of researchers working across AI, finance, and economics, built for PBCSF (Tsinghua University PBC School of Finance).

**Website:** https://easonai-5589.github.io/ai-talent-network/

The bibliographic snapshot was generated on 15 October 2026 and contains 754 candidates from 38 universities: 13 in Asia (mainland China, Hong Kong, and Singapore), 23 in the United States (U.S. News 2026 Best National Universities top 20, including the four schools tied at 20th), and 2 in Europe (expansion to the rest of Europe is on hold). The default shortlist has 10 candidates per continent. Current appointment evidence is maintained separately, with its own check dates and coverage shown on the page; the latest review of current institutions, titles and departments was completed on 21 October 2026. Chinese names are shown only where a source confirms them. This is a research demo, not a fully verified faculty directory or a final recruiting recommendation.

The full selection process, screening thresholds and scoring formulas are documented in [docs/selection-criteria.md](docs/selection-criteria.md) (Chinese) and in the site's 评选标准 section.

## School, position, and project tier

- **Current institution and position:** supported by the linked appointment source, with a check date. Missing or conflicting evidence is shown as pending rather than inferred from a paper affiliation or an old note.
- **Discovery affiliation:** the school used to find the candidate through publications and OpenAlex institution associations. Historical employment, visiting affiliations, and associated campuses can all appear here; this field does not establish current employment.
- **Our tier:** L1 top awards; L2 high-impact candidates; L3 field-core candidates; L4 other candidates. Membership uses the existing award, bibliometric, and manual rules. These are project labels, not official job titles, age or career-stage claims, or hiring decisions.

Legacy verification notes remain expandable for provenance. In particular, an old note saying that no individual search was performed is not treated as verified employment. The initial shortlist remains a review queue, including records whose current appointments need checking.

## Use the demo

- Search by name, current institution, position, and research topic; filter separately by discovery school, current institution, discipline, project tier, and appointment evidence status.
- Expand a researcher to inspect papers and public source links.
- Edit the shortlist and copy results to a spreadsheet.

Shortlist edits are saved in the current browser only. They are not shared with other visitors. A new browser or domain starts with the default shortlist.

## Hosting and updates

GitHub Pages serves `index.html` directly from the root of `main`. The page includes its styles, scripts, and dataset; it does not require a backend, an API key, or a Claude account. Google Fonts is optional and has local font fallbacks.

The publication sources are `src/template.html`, `src/catalog.js` and `data/talent.json`. Appointment corrections are stored independently in `data/current_roles_verified.json`; each record includes the institution, position, source URL, check date, and evidence status. Dated outcomes for people whose current post could not be confirmed are in `data/role_search_log.json`; `data/profile_discovery.json` holds official homepage links, and `display_affiliation.py` with `data/qs_world_rankings.json` chooses the one school shown for people with several appointments. To rebuild after editing them:

```sh
python3 build_page.py
```

To import bibliographic data from a freshly generated standalone HTML file while keeping this repository's presentation and appointment evidence:

```sh
python3 sync_page.py /path/to/ai-talent-network.html
python3 -m http.server 8765 --bind 127.0.0.1
```

Review the local page, commit the sources and updated `index.html`, and push `main` to deploy. The import validates the embedded dataset and preserves local appointment evidence; it does not crawl external sources. A successful push is not deployment verification: check the Pages run and the live page.

## Sources and limitations

Bibliographic data comes from [OpenAlex](https://openalex.org/) (CC0), supplemented by public institutional sources linked in the demo. Affiliation, title, author identity, and relevance can be incomplete or outdated; consult the record-level notes and original sources. The current snapshot includes duplicate author records and unresolved verification flags.

Only the website sources, public researcher data/evidence, and publication instructions are stored here. Local credentials, crawler caches, environments, and conversation records are excluded.
