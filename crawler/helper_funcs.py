from pathlib import Path
from typing import List
from urllib.parse import urlparse
import json

from .crawler_model import CrawlResults

DATA_DIR = Path("data")
GLOBAL_RESULT_FILE = DATA_DIR / "crawl_result.json"
DATA_DIR.mkdir(exist_ok=True)


def filter_urls_by_sitemap(urls: List):
    
    urls = [u for u in urls if "clearance2" not in u["url"]]
    urls = [u for u in urls if "gadmissions" not in u["url"]]
    urls = [u for u in urls if "cms." not in u["url"]]
    urls = [u for u in urls if "tender-notice" not in u["url"]]

    return urls


def make_safe_filename(url: str) -> str:

    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "index"
    safe_name = f"{parsed.netloc}_{path}"
    return safe_name

def save_crawl_result(result, crawl_data_dir: Path = DATA_DIR) -> CrawlResults:
   
    slug = make_safe_filename(result.url)
    folder = crawl_data_dir / slug
    folder.mkdir(exist_ok=True, parents=True)

    markdown_path = folder / "page.md"
    html_path = folder / "page.html"

    # Save markdown
    if result.markdown:
        md_text = (
            result.markdown.body
            if hasattr(result.markdown, "body")
            else result.markdown
        )
        markdown_path.write_text(md_text or "", encoding="utf-8")

    # Save cleaned HTML
    if result.cleaned_html:
        html_path.write_text(result.cleaned_html, encoding="utf-8")

    # Prepare metadata model
    duration = None
    memory = None
    if result.dispatch_result:
        dr = result.dispatch_result
        duration = (dr.end_time - dr.start_time)
        memory = dr.memory_usage

    crawl_result = CrawlResults(
        url=result.url,
        status_code=result.status_code,
        success=result.success,
        markdown_path=str(markdown_path) if markdown_path.exists() else None,
        html_path=str(html_path) if html_path.exists() else None,
        pdf_path=None,
        metadata=result.metadata,
        error_message=result.error_message,
        duration_seconds=duration,
        memory_usage_mb=memory
    )

    GLOBAL_RESULT_FILE.mkdir(exist_ok=True, parents=True)

    # Load existing data
    if GLOBAL_RESULT_FILE.exists():
        try:
            with GLOBAL_RESULT_FILE.open("r", encoding="utf-8") as f:
                all_results = json.load(f)
        except json.JSONDecodeError:
            all_results = []
    else:
        all_results = []

    # Append new result
    all_results.append(crawl_result.dict())

    # Save back
    with GLOBAL_RESULT_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    return crawl_result

