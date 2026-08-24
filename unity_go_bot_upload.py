# pylint: disable=line-too-long
"""
Uploads formatted wiki pages to the MediaWiki instance via pywikibot.
Reads pages_wiki_content.json and pushes each page in order:
  1. Template pages (cargo_declare + cargo_store)
  2. Data pages (template calls per record)
"""
import json
import os
from pathlib import Path
from sys import stdout
import pywikibot



ROOT_PATH = Path(__file__).parent

CONTENT_PAGES_KEY = "pages_content"
CONTENT_PAGES_TITLE_KEY = "title"
CONTENT_PAGES_CONTENT_KEY = "contents"

EDIT_SUMMARY = "Automated data import from unity_to_mw_cargo"

TESTING_PAGE_LIMIT = 5



def connect_site() -> pywikibot.Site:
    """Connects to the wiki."""
    os.environ["PYWIKIBOT_DIR"] = str(ROOT_PATH)
    site = pywikibot.Site()
    site.login()
    return site



def upload_page(site: pywikibot.Site, title: str, content: str, dry_run: bool = False) -> None:
    """Uploads a single page to the wiki."""
    page = pywikibot.Page(site, title)
    page.text = content
    if dry_run:
        stdout.write(f"[DRY RUN] Would upload: {title}\n")
        return
    page.save(summary=EDIT_SUMMARY, minor=False)
    stdout.write(f"Uploaded: {title}\n")



def go_bot_upload(pages: list, verbose: bool = False, testing: bool = False, dry_run: bool = False) -> None:
    """Uploads all pages to the wiki."""
    site = connect_site()
    for i, page in enumerate(pages):
        if testing and i >= TESTING_PAGE_LIMIT:
            break
        title = page[CONTENT_PAGES_TITLE_KEY]
        content = page[CONTENT_PAGES_CONTENT_KEY]
        if verbose:
            stdout.write(f"Uploading page {title} ({i+1} of {len(pages)})...\n")
        upload_page(site, title, content, dry_run=dry_run)
        if verbose:
            stdout.write(f"...done with {title}\n")



if __name__ == "__main__":
    with open(ROOT_PATH / "pages_wiki_content.json", "r", encoding="utf-8") as file:
        loaded_pages = json.load(file)
    all_pages = loaded_pages[CONTENT_PAGES_KEY]
    stdout.write(f"Uploading {len(all_pages)} pages to the wiki...\n")
    go_bot_upload(all_pages, verbose=True, testing=True, dry_run=False)
    stdout.write("...done.\n")
