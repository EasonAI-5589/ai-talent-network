# PBCSF AI Talent Dashboard

An interactive directory of researchers working across AI, finance, and economics, built for PBCSF (Tsinghua University PBC School of Finance).

**Website:** https://easonai-5589.github.io/ai-talent-network/

The bibliographic snapshot was generated on 15 October 2026 from 38 universities: 13 in Asia (mainland China, Hong Kong, and Singapore), 23 in the United States (U.S. News 2026 Best National Universities top 20, including the four schools tied at 20th), and 2 in Europe (University of Oxford and LSE). The site lists the 653 of 754 candidates whose current appointment is verified on an official university page (`apply_showcase` in `build_page.py`); the latest review of current institutions, titles and departments was completed on 21 October 2026. The default shortlist holds the top 10 researchers per continent by composite score. Chinese names are shown where a source confirms them.

Each researcher's search record (the school and query that found them, the actual value behind every screening threshold, the score breakdown, every cross paper and the appointment source) is in `data/search_evidence.json`, shown on their profile card (link: `#p-<OpenAlex id>`) and exported by `export_excel.py` to `downloads/pbcsf-ai-talent-search-evidence.xlsx` (`uvx --with openpyxl python export_excel.py`); run `uvx --with openpyxl python audit_release.py` before publishing to confirm the page and the workbook agree. The selection process, screening thresholds and scoring formulas are documented in [docs/selection-criteria.md](docs/selection-criteria.md) (Chinese) and in the site's 评选标准 section.

## School, position, and tier

- **Current institution and position:** taken from the linked official appointment page, with its check date. Where a researcher holds several appointments, the page shows the school ranked highest in the QS World University Rankings 2027, with that school's own title and department.
- **Search school:** the school whose publications led to the researcher in OpenAlex. It is kept separately from the current institution.
- **Tier:** L1 top awards; L2 high-impact researchers; L3 field-core researchers; L4 others. Tiers follow the award and bibliometric rules in the 评选标准 section.

## Use the site

- Search by name, current institution, position, and research topic; combine filters for region, search school, current institution, title, research theme, method, and department.
- Expand a researcher to see the appointment source, search evidence, score breakdown, and papers.
- Edit the shortlist and copy results to a spreadsheet, or download the Excel workbook.

Shortlist edits are saved in the current browser only. A new browser or domain starts with the default shortlist.

## Hosting and updates

GitHub Pages serves `index.html` directly from the root of `main`. The page includes its styles, scripts, and dataset; it does not require a backend or an API key. Google Fonts loads without blocking the page, and system fonts are used where it is unavailable.

The publication sources are `src/template.html`, `src/catalog.js` and `data/talent.json`. Appointment records are stored independently in `data/current_roles_verified.json`; each record includes the institution, position, department (Chinese, with the official English wording in `*_en` fields), source URL, check date, and evidence status. Dated outcomes for people whose current post could not be confirmed are in `data/role_search_log.json`; `data/profile_discovery.json` holds official homepage links, and `display_affiliation.py` with `data/qs_world_rankings.json` chooses the one school shown for people with several appointments. To rebuild after editing them:

```sh
python3 build_page.py
```

To import bibliographic data from a freshly generated standalone HTML file while keeping this repository's presentation and appointment evidence:

```sh
python3 sync_page.py /path/to/ai-talent-network.html
python3 -m http.server 8765 --bind 127.0.0.1
```

Review the local page, commit the sources and updated `index.html`, and push `main` to deploy. The import validates the embedded dataset and preserves local appointment evidence; it does not crawl external sources. A successful push is not deployment verification: check the Pages run and the live page.

## Sources

Bibliographic data comes from [OpenAlex](https://openalex.org/) (CC0); current appointments come from the official university pages linked on each profile card.

Only the website sources, public researcher data/evidence, and publication instructions are stored here. Local credentials, crawler caches, environments, and conversation records are excluded.
