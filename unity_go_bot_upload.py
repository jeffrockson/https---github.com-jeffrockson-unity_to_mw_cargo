# pylint: disable=line-too-long, too-many-arguments, too-many-positional-arguments
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

TEMPLATE_NAMESPACE = "Template"
DATA_NAMESPACE = "Data"

EDIT_SUMMARY = "Automated data import from unity_to_mw_cargo"

TESTING_PAGE_LIMIT = 5



def connect_site() -> pywikibot.Site:
    """Connects to the wiki."""
    os.environ["PYWIKIBOT_DIR"] = str(ROOT_PATH)
    site = pywikibot.Site()
    site.login()
    return site



def upload_page(site: pywikibot.Site, title: str, content: str, verbose: bool, dry_run: bool = False) -> None:
    """Uploads a single page to the wiki."""
    pywikibot.config.verbose_output = verbose
    page = pywikibot.Page(site, title)
    page.text = content
    if dry_run:
        stdout.write(f"[DRY RUN] Would upload: {title}\n")
        return
    page.save(summary=EDIT_SUMMARY, minor=False)



# pylint: disable=unused-argument
def upload_by_namespace(site: pywikibot.Site, namespace: str, pages: list, verbose: bool, testing: bool, dry_run: bool) -> None:
    """Uploads all pages in a namespace to the wiki."""
    if verbose:
        stdout.write(f"Uploading namespace {namespace} pages...\n")
    for i, page in enumerate(pages):
        if testing and i >= TESTING_PAGE_LIMIT:
            break
        title = page[CONTENT_PAGES_TITLE_KEY]
        content = page[CONTENT_PAGES_CONTENT_KEY]
        if not title.startswith(namespace + ":"):
            continue
        if verbose:
            stdout.write(f"...uploading {title} ({i+1} of {len(pages)})...")
        upload_page(site, title, content, verbose, dry_run=dry_run)
    if verbose:
        stdout.write(f"...done with namespace {namespace}.\n")



def recreate_cargo_tables(site: pywikibot.Site, pages: list, verbose: bool, testing: bool, dry_run: bool) -> None:
    """Triggers Cargo to create tables for all template pages."""
    pywikibot.config.verbose_output = verbose
    if verbose:
        stdout.write("(Re)creating cargo tables...\n")
    for i, page in enumerate(pages):
        if testing and i >= TESTING_PAGE_LIMIT:
            break
        title = page[CONTENT_PAGES_TITLE_KEY]
        if not title.startswith(TEMPLATE_NAMESPACE + ":"):
            continue
        if dry_run:
            stdout.write(f"...[DRY RUN] Would recreate Cargo table for: {title}...\n")
            continue
        if verbose:
            stdout.write(f"...recreating cargo table for: {title}...\n")
        template_name = title.removeprefix(TEMPLATE_NAMESPACE + ":")
        token = site.tokens["csrf"]
        site.simple_request(action="cargorecreatetables", template=template_name, token=token).submit()
    if verbose:
        stdout.write("...done with cargo tables.\n")



def go_bot_upload(pages: list, verbose: bool = False, testing: bool = False, dry_run: bool = False) -> None:
    """Uploads all pages to the wiki."""
    site = connect_site()
    upload_by_namespace(site, TEMPLATE_NAMESPACE, pages, verbose, testing, dry_run)
    recreate_cargo_tables(site, pages, verbose, testing, dry_run)
    site.simple_request(action="runJobs").submit()
    upload_by_namespace(site, DATA_NAMESPACE, pages, verbose, testing, dry_run)



if __name__ == "__main__":
    with open(ROOT_PATH / "pages_wiki_content.json", "r", encoding="utf-8") as file:
        loaded_pages = json.load(file)
    all_pages = loaded_pages[CONTENT_PAGES_KEY]
    stdout.write(f"Uploading {len(all_pages)*3} pages to the wiki...\n")
    go_bot_upload(all_pages, verbose=False, testing=False, dry_run=False)
    stdout.write("...done.\n")
