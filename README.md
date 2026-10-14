# AI Talent Network

An interactive pilot directory of researchers working across AI, finance, and economics.

**Website:** https://easonai-5589.github.io/ai-talent-network/

The current snapshot was generated on 14 October 2026 at 23:18 and contains 373 records across 15 universities, with a default shortlist of 30 researchers. Records include provisional classifications and verification notes. This is a research demo, not a fully verified faculty directory or a final recruiting recommendation.

## Use the demo

- Search by name and research topic; filter by school, region, discipline, tier, and verification status.
- Expand a researcher to inspect papers and public source links.
- Edit the shortlist and copy results to a spreadsheet.

Shortlist edits are saved in the current browser only. They are not shared with other visitors. A new browser or domain starts with the default shortlist.

## Hosting and updates

GitHub Pages serves `index.html` directly from the root of `main`. The page includes its styles, scripts, and dataset; it does not require a backend, an API key, or a Claude account. Google Fonts is optional and has local font fallbacks.

To update the publication from a freshly generated standalone HTML file:

```sh
python3 sync_page.py /path/to/ai-talent-network.html
python3 -m http.server 8765 --bind 127.0.0.1
```

Review the local page, commit the updated `index.html`, and push `main` to deploy. The sync command validates the embedded dataset before copying and does not crawl or modify researcher records.

## Sources and limitations

Bibliographic data comes from [OpenAlex](https://openalex.org/) (CC0), supplemented by public institutional sources linked in the demo. Affiliation, title, author identity, and relevance can be incomplete or outdated; consult the record-level notes and original sources. The current snapshot includes duplicate author records and unresolved verification flags.

Only the standalone website and publication instructions are stored here. Local credentials, crawler caches, environments, and conversation records are excluded.
