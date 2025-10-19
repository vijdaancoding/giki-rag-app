import asyncio
from typing import List, Set, Dict
from pathlib import Path
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from crawl4ai import (
    AsyncUrlSeeder, 
    AsyncWebCrawler, 
    SeedingConfig, 
    CrawlerRunConfig, 
    CacheMode, 
    BrowserConfig, 
    BFSDeepCrawlStrategy,
    FilterChain,
    DomainFilter
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher
from crawl4ai.content_filter_strategy import PruningContentFilter

from utils.logger_utils import create_logger

# Configurations
BASE_URL = "https://giki.edu.pk"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True) 

# Logger Init
logger = create_logger("crawl_logger")


class GIKICrawler:
    def __init__(self):
        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.url_metadata: Dict[str, Dict] = {}

    async def discover_all_urls(self) -> List[Dict]:
        """
        1. Get URLs from Sitemap
        2. Get URLs from Common Crawl
        3. Get URL metadata
        """

        config = SeedingConfig(
            source="sitemap+cc",
            extract_head=True,
            pattern="*",
            max_urls=10000,
            live_check=False, # GIKI has many dead URLs we want to fetch
            force=False, # Use Cache for Effeciency
            verbose=True
        )

        async with AsyncUrlSeeder() as seeder:
            urls = await seeder.urls(BASE_URL, config)

        logger.info(f"Total URLs Extracted: {len(urls)}")
        
        # Store metadata
        for url_data in urls:
            self.url_metadata[url_data['url']] = {
                'head_data': url_data.get('head_data', {}),
                'source': url_data.get('source', 'unknown')
            }
        
        return urls

    def categorize_urls(self, urls: List[Dict]) -> Dict[str, List[str]]:
        """
        Categorize URLs by Content Type
        """

        categories = {
            'academics': [],
            'admissions': [],
            'research': [],
            'faculty': [],
            'students': [],
            'departments': [],
            'news': [],
            'events': [],
            'administration': [],
            'facilities': [],
            'other': []
        }

        # Define patterns for each category
        patterns = {
            'academics': [r'/academic', r'/program', r'/course', r'/curriculum', r'/degree', r'/courses'],
            'admissions': [r'/admission', r'/apply', r'/entry', r'/undergraduate', r'/graduate', r'/admissions', r'/job-opportunities', r'/scholarship'],
            'research': [r'/research', r'/publication', r'/lab', r'/project'],
            'faculty': [r'/faculty', r'/staff', r'/professor', r'/teacher', r'/people', r'/personnel', r'/personnel_category'],
            'students': [r'/student', r'/campus-life', r'/hostel', r'/societies', r'lds', r'naqsh', r'cbs', r'science-society', r'media-club', r'ashrae', r'wes', r'netronix', r'les', r'sports-society', r'acm', r'project-topi', r'aiesec', r'spie', r'aiaa'],
            'departments': [r'/department', r'/school', r'/institute', r'/center', r'/fcse', 'r/fme', 'r/mgs', 'r/fes', 'r/fbs', 'r/fme', r'/ai', r'/fmce', r'/cs', r'/ce', r'/ch'],
            'news': [r'/news', r'/announcement', r'/media'],
            'events': [r'/event', r'/seminar', r'/workshop', r'/conference', r'event-calendar'],
            'administration': [r'/administration', r'/office', r'/registrar', r'/controller'],
            'facilities': [r'/facility', r'/library', r'/sports', r'/health']
        }

        for url_data in urls:
            url = url_data['url']
            categorized = False
            
            # Try to categorize by URL pattern
            for category, pattern_list in patterns.items():
                if any(re.search(p, url, re.IGNORECASE) for p in pattern_list):
                    categories[category].append(url)
                    categorized = True
                    break
            
            # Try to categorize by page title
            if not categorized:
                head_data = url_data.get('head_data', {})
                title = head_data.get('title', '').lower()
                
                for category, pattern_list in patterns.items():
                    if any(re.search(p.strip('/'), title) for p in pattern_list):
                        categories[category].append(url)
                        categorized = True
                        break
            
            if not categorized:
                categories['other'].append(url)
        

        # Print category statistics
        logger.info("\nURL Distribution by Category:")
        for category, urls in categories.items():
            if urls:
                logger.info(f"{category}: {len(urls)} URLs")
        
        return categories

    def filter_urls(self, urls: List[Dict]) -> List[Dict]:
        """
        Remove only clearly irrelevant URLs, not potentially important ones
        """
        # Be more selective with filtering
        exclude_patterns = [
            r'/wp-admin',
            r'/wp-content',
            r'/wp-includes',
            r'\?replytocom=',
            r'/feed/',
            r'/xmlrpc\.php',
            # Only exclude specific problematic paths
            r'/cms',  # CMS subdomain
        ]
        
        
        filtered = []
        for url_data in urls:
            url = url_data['url']
            
            # Skip if matches exclude pattern
            if any(re.search(p, url, re.IGNORECASE) for p in exclude_patterns):
               logger.info(f"Skipping: {url}")
               continue
            
            # Skip duplicate URLs (same path, different params)
            parsed = urlparse(url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            if clean_url in self.discovered_urls:
                continue
            
            self.discovered_urls.add(clean_url)
            filtered.append(url_data)
        
        logger.info(f"\nFiltered to {len(filtered)} unique URLs")
        return filtered
    
    async def deep_crawl_discovery(self, seed_urls: List[str], max_depth: int = 2) -> List[str]:
        """
        This catches pages not in sitemap
        """
        print(f"\nStarting deep crawl (max depth: {max_depth})...")
        
        filter_chain = FilterChain([
            DomainFilter(allowed_domains=["giki.edu.pk"])
        ])
        
        deep_crawl_config = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=max_depth,
                max_pages=1000,
                include_external=False,
                filter_chain=filter_chain
            ),
            cache_mode=CacheMode.ENABLED,
            stream=True,
            only_text=True,  # Just discover URLs, don't need full content
            verbose=False
        )
        
        discovered = set()
        
        async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
            # Use a few seed URLs from each category for discovery
            async for result in await crawler.arun(
                url=BASE_URL,
                config=deep_crawl_config
            ):
                if result.success:
                    discovered.add(result.url)
                    # Also extract internal links
                    if hasattr(result, 'links') and result.links:
                        for link in result.links.get('internal', []):
                            discovered.add(link['href'])
        
        new_urls = discovered - self.discovered_urls
        logger.info(f"Deep crawl discovered {len(new_urls)} additional URLs")
        
        return list(new_urls)
    
    async def crawl_pages(self, urls: List[str], batch_size: int = 50):
        """
        Crawl All Pages with Smart Content Extraction
        """
        
        # Configure markdown generation with content filtering
        md_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.48,
                threshold_type="dynamic"
            ),
            options={
                "citations": True,
                "body_width": 100
            }
        )
        
        crawl_config = CrawlerRunConfig(
            excluded_tags=["header", "footer", "nav", "form", "aside", "script", "style"],
            markdown_generator=md_generator,
            cache_mode=CacheMode.ENABLED,
            stream=False,
            screenshot=False,  # Disable for speed
            pdf=False
        )
        
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=80.0,
            check_interval=1.0,
            max_session_permit=10
        )
        
        results = []
        
        # Crawl in batches to avoid overwhelming system
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            logger.info(f"\nProcessing batch {i//batch_size + 1}/{(len(urls)-1)//batch_size + 1}")
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                try:
                    batch_results = await crawler.arun_many(
                        urls=batch,
                        config=crawl_config,
                        dispatcher=dispatcher
                    )
                    
                    for result in batch_results:
                        if result and result.success:
                            self.crawled_urls.add(result.url)
                            results.append(result)
                            logger.info(f"{result.url}")
                        else:
                            if result:
                                self.failed_urls.add(result.url)
                                logger.error(f"{result.url}: {result.error_message}")
                
                except Exception as e:
                    logger.error(f"Batch error: {e}")
                    for url in batch:
                        self.failed_urls.add(url)
            
            # Small delay between batches
            await asyncio.sleep(2)
        
        logger.info(f"\nCrawled {len(results)} pages successfully")
        logger.error(f"Failed: {len(self.failed_urls)} pages")
        
        return results
    
    def save_results(self, results: List, categories: Dict[str, List[str]]):
        """
        Save Results with Smart Organization
        """
        
        # Create category directories
        for category in categories.keys():
            (DATA_DIR / category).mkdir(exist_ok=True)
        
        # Reverse lookup: URL -> category
        url_to_category = {}
        for category, urls in categories.items():
            for url in urls:
                url_to_category[url] = category
        
        saved_count = 0
        
        for result in results:
            if not result.success:
                continue
            
            # Determine category
            category = url_to_category.get(result.url, 'other')
            
            # Create safe filename
            parsed = urlparse(result.url)
            path = parsed.path.strip('/').replace('/', '_') or 'index'
            filename = f"{parsed.netloc}_{path}"
            
            # Save in category folder
            folder = DATA_DIR / category / filename
            folder.mkdir(exist_ok=True, parents=True)
            
            # Save markdown (preferred - cleaner)
            if result.markdown:
                md_path = folder / "content.md"
                md_text = (
                    result.markdown.fit_markdown or 
                    result.markdown.raw_markdown
                )
                md_path.write_text(md_text or "", encoding="utf-8")
            
            # Save HTML (for reference)
            if result.cleaned_html:
                html_path = folder / "content.html"
                html_path.write_text(result.cleaned_html, encoding="utf-8")
            
            # Save metadata
            metadata = {
                'url': result.url,
                'category': category,
                'title': result.metadata.get('title', ''),
                'crawled_at': datetime.utcnow().isoformat(),
                'status_code': result.status_code,
                'metadata': result.metadata
            }
            
            metadata_path = folder / "metadata.json"
            with metadata_path.open('w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            saved_count += 1
        
        logger.info(f"Saved {saved_count} pages")
        
        # Save crawl statistics
        stats = {
            'total_discovered': len(self.discovered_urls),
            'total_crawled': len(self.crawled_urls),
            'total_failed': len(self.failed_urls),
            'categories': {k: len(v) for k, v in categories.items()},
            'crawl_date': datetime.utcnow().isoformat()
        }
        
        stats_path = DATA_DIR / "crawl_stats.json"
        with stats_path.open('w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"\nStatistics saved to {stats_path}")
        
        # Save failed URLs for retry
        if self.failed_urls:
            failed_path = DATA_DIR / "failed_urls.txt"
            failed_path.write_text('\n'.join(sorted(self.failed_urls)))
            logger.error(f"Failed URLs saved to {failed_path} for retry")


async def main():
    crawler = GIKICrawler()
    
    # Step 1: Discover all URLs
    urls = await crawler.discover_all_urls()
    
    # Step 2: Categorize URLs
    categories = crawler.categorize_urls(urls)
    
    # Step 3: Filter URLs
    filtered = crawler.filter_urls(urls)
    
    # Step 4: Deep crawl to discover more
    additional_urls = await crawler.deep_crawl_discovery(
        seed_urls=[BASE_URL],
        max_depth=2  # Increase if needed
    )
    
    # Add newly discovered URLs to filtered list
    for url in additional_urls:
        if url not in crawler.discovered_urls:
            filtered.append({'url': url})
            # Categorize new URLs
            for cat, cat_urls in categories.items():
                if any(re.search(p, url) for p in [r'/'+cat]):
                    categories[cat].append(url)
                    break
    
    # Step 5: Crawl all pages
    all_urls = [u['url'] if isinstance(u, dict) else u for u in filtered]
    results = await crawler.crawl_pages(all_urls)
    
    # Step 6: Save results
    crawler.save_results(results, categories)
    
    logger.info("\nCrawl complete!")
    logger.info(f"Total pages crawled: {len(crawler.crawled_urls)}")
    logger.info(f"Data saved in: {DATA_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
