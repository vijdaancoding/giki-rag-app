import asyncio
from typing import List
from pathlib import Path
import json
from crawl4ai import (
    AsyncUrlSeeder, 
    AsyncWebCrawler, 
    SeedingConfig, 
    CrawlerRunConfig, 
    CacheMode, 
    BrowserConfig, 
    CrawlerMonitor, 
    DisplayMode
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher

from .helper_funcs import (
    filter_urls_by_sitemap,
    make_safe_filename,
    save_crawl_result
)
from .crawler_model import CrawlResults
from utils.logger_utils import create_logger

URL_TO_CRAWL = "https://giki.edu.pk"

logger = create_logger("crawl_logger")


async def get_live_urls():

    config = SeedingConfig(
        source="sitemap+cc", # Only use sitemap not Common Crawl since its too excessive
        extract_head=True, # Get page metadata
        pattern="*", # Fetch all URLS (will filter later)
        verbose=True, # for testing purpose
        force=True
    )

    async with AsyncUrlSeeder() as seeder:
        urls = await seeder.urls(URL_TO_CRAWL, config)

    urls = filter_urls_by_sitemap(urls)
    
    logger.info(f"Total URLs Extracted: {len(urls)}")
    
    return urls

async def crawl_pages(urls: List[str]):
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        # enable_stealth=True # just in case if GIKI uses bot detection LMAO most prolly not
    )

    md_generator = DefaultMarkdownGenerator(
        options={"citations": True, "body-width": 100}
    )

    crawl_config = CrawlerRunConfig(
        excluded_tags=["header", "footer", "nav", "form", "aside"],
        markdown_generator=md_generator,
        cache_mode=CacheMode.ENABLED,
        stream=False
    )

    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=80.0,
        check_interval=1.0,
        max_session_permit=10,
        # monitor=CrawlerMonitor(
        #    display_mode=DisplayMode.DETAILED
        # )
    )

    stored_results = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            results = await crawler.arun_many(
                urls=urls,
                config=crawl_config,
                dispatcher=dispatcher
            )
            
            if not results:
                logger.error(f"Crawler returned None, skipping batch")
                return stored_results
        
        except Exception as e:
            logger.error(f"Crashed Playwright: {e}")
            return stored_results
        
        for result in results:
            if result is None:
                logger.warning("Received None result from crawler, Skipping...")
                continue

            if result.success:
                dr = result.dispatch_result
                logger.info(f"Successfully Crawled URL {result.url} | Memory: {dr.memory_usage:.1f}MB | Duration: {dr.end_time - dr.start_time}")
                stored = save_crawl_result(result)
                stored_results.append(stored)
            elif result.status_code == 403 and "robots.txt" in result.error_message:
                logger.warning(f"Skipped URL {result.url} - blocked by robots.txt")
            else:
                logger.error(f"Failed to Crawl URL: {result.url}: {result.error_message}")

        return stored_results


async def main():
    urls_data = await get_live_urls()
    urls = [u["url"] for u in urls_data]
    await crawl_pages(urls)


if __name__ == "__main__":
    asyncio.run(main())
        
                
