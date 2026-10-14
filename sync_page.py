"""Import a standalone demo's dataset, then rebuild with local presentation and role evidence."""

import argparse
import json
from pathlib import Path

import build_page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Generated standalone HTML to import")
    args = parser.parse_args()
    try:
        data = build_page.import_dataset(build_page.extract_dataset(args.source.read_text(encoding="utf-8")))
        # Validate the complete local build before replacing the source dataset.
        build_page.prepare_page(data)
        build_page.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        build_page.DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = build_page.build()
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
