import re
from hashlib import sha1
import json
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm

# Your existing navigation items
NAV_ITEMS = {
    "VISION & MISSION",
    "APPLY FOR ADMISSION",
    "ADMINISTRATION",
    "CAMPUS LIFE",
    "OVERVIEW",
    "BOARD OF GOVERNORS",
    "PRESIDENT'S MESSAGE",
    "RECTOR'S MESSAGE",
    "ACADEMIC POLICY",
    "ACADEMIC CALENDAR",
    "LIBRARY",
    "STUDENT AFFAIRS",
    "OFFICE OF ADMISSION & EXAMINATION",
    "QUALITY ENHANCEMENT CELL",
    "ORIC",
    "ELECTRICAL ENGINEERING",
    "COMPUTER SCIENCES AND ENGINEERING",
    "BASIC SCIENCES",
    "MECHANICAL ENGINEERING",
    "MATERIAL SCIENCE & CHEMICAL ENGINEERING",
    "DEPARTMENT OF CIVIL ENGINEERING",
    "SCHOOL OF MANAGEMENT SCIENCES",
    "ADMISSION OPEN: APPLY NOW",
    "UNDERGRADUATE SCHOLARSHIPS",
    "GRADUATE SCHOLARSHIP",
    "SCHOLARSHIPS",
    "ALUMNI",
    "QEC & ACCREDITATION",
    "SOPREST",
    "TENDERS & NOTICES",
    "NEWSLETTERS",
    "IT",
    "IT HELPDESK",
    "SDGIKI",
    "SDGIKI NEWSLETTER VOLUME 02",
    "SDGIKI | NEWSLETTER | VOL 01",
    "SDGIKI | NEWSLETTER | VOL 02",
    "SDGIKI | NEWSLETTER | VOL 03",
    "NEWSLETTER | SPRING 2024",
    "NEWSLETTER | FALL 2023",
    "NEWSLETTER | SPRING 2023",
    "NEWSLETTER | FALL 2022",
    "NEWSLETTER | SPRING 2022",
    "NEWSLETTER | FALL 2021",
    "ANNUAL REPORT",
    "ANNUAL REPORT 2023",
    "ANNUAL REPORT 2022",
    "ANNUAL REPORT 2021",
    "SDG 1: NO POVERTY",
    "SDG 2: ZERO HUNGER",
    "SDG 3: GOOD HEALTH AND WELL-BEING",
    "SDG 4: QUALITY EDUCATION",
    "SDG 5: GENDER EQUALITY",
    "SDG 6: CLEAN WATER AND SANITATION",
    "SDG 7: AFFORDABLE AND CLEAN ENERGY",
    "SDG 8: DECENT WORK AND ECONOMIC GROWTH",
    "SDG 9: INDUSTRY INNOVATION AND INFRASTRUCTURE",
    "SDG 10: REDUCED INEQUALITIES",
    "SDG 11: SUSTAINABLE CITIES AND COMMUNITIES",
    "SDG 12: RESPONSIBLE CONSUMPTION AND PRODUCTION",
    "SDG 13: CLIMATE ACTION",
    "SDG 14: LIFE BELOW WATER",
    "SDG 15: LIFE ON LAND",
    "SDG 16: PEACE, JUSTICE, AND STRONG INSTITUTION",
    "SDG 17: PARTNERSHIP FOR GOALS",
    "IT TRAINING PROGRAM",
    "SERVICES",
    "CAREERS",
    "CONTACT US",
}


def extract_clean_text(md_path: Path) -> str:
    """
    Extract and clean text from markdown file
    Keeps your existing cleaning logic
    """
    if not md_path.exists():
        return ""
    
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"Error reading {md_path}: {e}")
        return ""

    # --- Remove HTML tags ---
    text = re.sub(r"<[^>]+>", "", text)

    # --- Remove Markdown image links ---
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    # --- Convert [text](url) → text ---
    text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)

    # --- Remove YAML frontmatter (if any) ---
    text = re.sub(r"^---.*?---", "", text, flags=re.DOTALL)

    # --- Split into lines for heuristic cleaning ---
    lines = text.splitlines()
    cleaned = []
    seen_lines = set()

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # --- Heuristic: remove nav/menu patterns ---
        if re.search(r'^\s*[*-]\s*\[.*\]\(https?://giki\.edu\.pk/(fme|#|wp-content|202\d|admissions|administration|campus-life)', stripped):
            continue
        if re.search(r'\[\]\(https?://', stripped):  # empty links
            continue
        if re.match(r'^\s*\[\!?\[', stripped):  # images/logos
            continue
        if re.search(r'#menu|#mm-|#kingster|menu-main-navigation', stripped, flags=re.I):
            continue
        if re.search(r'\bHOME\b|\bABOUT GIK\b|\bACADEMICS\b|\bADMISSIONS\b', stripped, flags=re.I):
            continue
        
        # Remove nav bullets
        if stripped.startswith("* "):
            # Check if it matches a known nav keyword
            if any(keyword.upper() in stripped.upper() for keyword in NAV_ITEMS):
                continue

        # --- Deduplication ---
        if stripped in seen_lines:
            continue
        
        seen_lines.add(stripped)
        
        cleaned.append(stripped)

    # --- Rejoin & collapse whitespace ---
    text = "\n".join(cleaned)
    text = re.sub(r'\n{2,}', '\n\n', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()

    return text

def stable_id(url: str) -> str:
    return sha1(url.encode("utf-8")).hexdigest()

def process_all_pages(data_dir: Path = Path("data")) -> List[Dict]:
    """
    Process all crawled pages in the new directory structure
    Returns list of cleaned records with metadata
    """
    records = []
    processed_count = 0
    error_count = 0
    
    # Get all category directories
    category_dirs = [d for d in data_dir.iterdir() 
                    if d.is_dir() and not d.name.startswith('.')]
    
    print(f"Found {len(category_dirs)} categories to process")
    
    # Process each category
    for category_dir in tqdm(category_dirs, desc="Processing categories"):
        category_name = category_dir.name
        
        # Get all page directories in this category
        page_dirs = [d for d in category_dir.iterdir() if d.is_dir()]
        
        for page_dir in tqdm(page_dirs, desc=f"Processing {category_name}", leave=False):
            try:
                # Paths to files
                md_path = page_dir / "content.md"
                metadata_path = page_dir / "metadata.json"
                
                # Check if files exist
                if not md_path.exists():
                    print(f"Warning: No markdown file in {page_dir}")
                    error_count += 1
                    continue
                
                if not metadata_path.exists():
                    print(f"Warning: No metadata file in {page_dir}")
                    error_count += 1
                    continue
                
                # Load existing metadata
                with metadata_path.open('r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Clean the markdown content
                cleaned_content = extract_clean_text(md_path)
                
                # Skip if content is too short (likely failed cleaning)
                if len(cleaned_content) < 10:
                    print(f"Warning: Content too short for {metadata.get('url', page_dir.name)}")
                    error_count += 1
                    continue
                
                # Save updated metadata back to file
                with metadata_path.open('w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                # Create record for Pinecone
                record = {
                    'id': stable_id(metadata['url']), 
                    'url': metadata['url'],
                    'category': metadata.get('category', category_name),
                    'title': metadata.get('title', ''),
                    'content': f"Category: {metadata.get('category', category_name)}\n\n{metadata.get('title', '')}\n\n{cleaned_content}",
                    'metadata_path': str(metadata_path),
                    'md_path': str(md_path)
                }
                
                records.append(record)
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing {page_dir}: {e}")
                error_count += 1
                continue
    
    print(f"\n✅ Processed {processed_count} pages successfully")
    print(f"❌ Errors: {error_count}")
    
    return records


def save_cleaned_records(records: List[Dict], output_path: Path = Path("data/cleaned_records.json")):
    """
    Save all cleaned records to a JSON file for reference
    """
    # Create a simplified version for saving (without full metadata)
    simplified = []
    for record in records:
        simplified.append({
            'url': record['url'],
            'category': record['category'],
            'title': record['title'],
            'content_preview': record['content'][:200] + "...",
            'content_length': len(record['content']),
            'metadata_path': record['metadata_path']
        })
    
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(simplified, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved cleaned records summary to {output_path}")


def get_stats(records: List[Dict]) -> Dict:
    """
    Get statistics about the cleaned data
    """
    if not records:
        return {}
    
    stats = {
        'total_pages': len(records),
        'categories': {},
        'avg_content_length': 0,
        'min_content_length': float('inf'),
        'max_content_length': 0,
        'total_content_chars': 0
    }
    
    for record in records:
        # Category stats
        category = record['category']
        stats['categories'][category] = stats['categories'].get(category, 0) + 1
        
        # Content length stats
        content_len = len(record['content'])
        stats['total_content_chars'] += content_len
        stats['min_content_length'] = min(stats['min_content_length'], content_len)
        stats['max_content_length'] = max(stats['max_content_length'], content_len)
    
    stats['avg_content_length'] = stats['total_content_chars'] / len(records)
    
    return stats


def main():
    """
    Main function to process all pages and prepare for Pinecone upload
    """
    print("=" * 60)
    print("GIKI Data Cleaning & Preparation")
    print("=" * 60)
    
    # Process all pages
    records = process_all_pages()
    
    if not records:
        print("❌ No records processed. Check your data directory.")
        return
    
    # Get statistics
    stats = get_stats(records)
    
    print("\n📊 Statistics:")
    print(f"  Total pages: {stats['total_pages']}")
    print(f"  Average content length: {stats['avg_content_length']:.0f} chars")
    print(f"  Min content length: {stats['min_content_length']} chars")
    print(f"  Max content length: {stats['max_content_length']} chars")
    print(f"\n  Pages by category:")
    for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
        print(f"    {category}: {count}")
    
    # Save cleaned records
    save_cleaned_records(records)
    
    print(f"\n✅ Cleaning complete! {len(records)} records ready for Pinecone upload")
    
    return records


if __name__ == "__main__":
    records = main()
