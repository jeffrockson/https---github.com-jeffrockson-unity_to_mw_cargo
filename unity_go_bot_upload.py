# pylint: disable=line-too-long, too-many-arguments, too-many-positional-arguments
"""
Uploads formatted wiki pages to the MediaWiki instance via pywikibot.
Reads pages_wiki_content.json and pushes each page in order:
  1. Template pages (cargo_declare + cargo_store)
  2. Data pages (template calls per record)

Pass an optional domain name to upload only that domain plus guid_index.
"""
import os
import json
import argparse
from pathlib import Path
from sys import stdout

import subprocess
import pywikibot



MEDIAWIKI_PATH = Path("C:/tools/mediawiki-1.44.2")

ROOT_PATH = Path(__file__).parent

CONTENT_PAGES_KEY = "pages_content"
CONTENT_PAGES_TITLE_KEY = "title"
CONTENT_PAGES_CONTENT_KEY = "contents"

TEMPLATE_NAMESPACE = "Template"
DATA_NAMESPACE = "Data"

TEMPLATE_NAME = "Dataloader"
GUID_INDEX = "guid_index"

EDIT_SUMMARY = "Automated data import from unity_to_mw_cargo"

TESTING_PAGE_LIMIT = 5



def connect_site() -> pywikibot.Site:
    """Connects to the wiki."""
    os.environ["PYWIKIBOT_DIR"] = str(ROOT_PATH)
    site = pywikibot.Site()
    site.login()
    return site



# pylint: disable=unused-argument
def upload_page(site: pywikibot.Site, title: str, content: str, verbose: bool, dry_run: bool = False) -> None:
    """Uploads a single page to the wiki."""
    page = pywikibot.Page(site, title)
    page.text = content
    if dry_run:
        stdout.write(f"[DRY RUN] Would upload: {title}\n")
        return
    page.save(summary=EDIT_SUMMARY, minor=False, quiet=True)



def filter_pages_for_domain(all_pages: list, domain: str) -> list:
    """Returns a list of pages for one domain plus guid_index."""
    domain_template = f"{TEMPLATE_NAMESPACE}:{TEMPLATE_NAME}/{domain}"
    domain_data_prefix = f"{DATA_NAMESPACE}:{domain}/"
    index_template = f"{TEMPLATE_NAMESPACE}:{TEMPLATE_NAME}/{GUID_INDEX}"
    index_data_prefix = f"{DATA_NAMESPACE}:{GUID_INDEX}/"
    return [
        page for page in all_pages
        if page[CONTENT_PAGES_TITLE_KEY] == domain_template
        or page[CONTENT_PAGES_TITLE_KEY].startswith(domain_data_prefix)
        or page[CONTENT_PAGES_TITLE_KEY] == index_template
        or page[CONTENT_PAGES_TITLE_KEY].startswith(index_data_prefix)
    ]



def upload_by_namespace(site: pywikibot.Site, namespace: str, pages: list, verbose: bool, testing: bool, dry_run: bool) -> None:
    """Uploads all pages in a namespace to the wiki."""
    if verbose:
        stdout.write(f"Uploading {namespace} namespace pages...\n")
    for i, page in enumerate(pages):
        if testing and i >= TESTING_PAGE_LIMIT:
            break
        title = page[CONTENT_PAGES_TITLE_KEY]
        content = page[CONTENT_PAGES_CONTENT_KEY]
        if not title.startswith(namespace + ":"):
            continue
        if verbose:
            stdout.write(f"...uploading {title} ({i+1} of {len(pages)})...\n")
        upload_page(site, title, content, verbose, dry_run=dry_run)
    if verbose:
        stdout.write(f"...done with {namespace} namespace.\n")



def rerun_cargo_table_maintenance(pages: list, verbose: bool, testing: bool, dry_run: bool) -> None:
    """Triggers Cargo to create tables for all template pages."""
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
        table_name = title.removeprefix(TEMPLATE_NAMESPACE + ":" + TEMPLATE_NAME + "/")
        subprocess.run(
            ["php", "maintenance/run.php", "Cargo:cargoRecreateData", "--table", table_name, "--quiet"],
            cwd=MEDIAWIKI_PATH,
            check=True,
        )
    subprocess.run(
        ["php", "maintenance/run.php", "runJobs"],
        cwd=MEDIAWIKI_PATH,
        check=True,
    )
    if verbose:
        stdout.write("...done with cargo tables.\n")



def go_bot_upload(wiki_content: dict, domain: str | None = None, verbose: bool = False, testing: bool = False, dry_run: bool = False) -> None:
    """Uploads pages to the wiki. When domain is set, uploads that domain and guid_index only."""
    site = connect_site()
    all_pages = wiki_content[CONTENT_PAGES_KEY]
    pages = filter_pages_for_domain(all_pages, domain) if domain else all_pages
    if domain and verbose:
        stdout.write(f"Filtered to domain {domain} and guid_index ({len(pages)} pages).\n")
    upload_by_namespace(site, TEMPLATE_NAMESPACE, pages, verbose, testing, dry_run)
    rerun_cargo_table_maintenance(pages, verbose, testing, dry_run)
    upload_by_namespace(site, DATA_NAMESPACE, pages, verbose, testing, dry_run)
    rerun_cargo_table_maintenance(pages, verbose, testing, dry_run)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload wiki pages from pages_wiki_content.json")
    parser.add_argument("domain", nargs="?", help="Single domain to upload (guid_index is always included)")
    args = parser.parse_args()
    with open(ROOT_PATH / "pages_wiki_content.json", "r", encoding="utf-8") as file:
        loaded_wiki_content = json.load(file)
    if args.domain:
        stdout.write(f"Uploading domain {args.domain} and guid_index to the wiki...\n")
    else:
        stdout.write(f"Uploading {len(loaded_wiki_content[CONTENT_PAGES_KEY])*2} pages to the wiki...\n")
    go_bot_upload(loaded_wiki_content, args.domain, verbose=True, testing=False, dry_run=False)
    stdout.write("...done.\n")
