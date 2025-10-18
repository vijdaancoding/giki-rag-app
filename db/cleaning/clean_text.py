import re
from pathlib import Path
import json

NAV_ITEMS = {
    "VISION & MISSION",
    "APPLY FOR ADMISSION",
    "ADMINISTRATION",
    "CAMPUS LIFE",
    "OVERVIEW",
    "BOARD OF GOVERNORS",
    "PRESIDENT’S MESSAGE",
    "RECTOR’S MESSAGE",
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


def extract_clean_text(md_path: str):
    path = Path(md_path)

    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8", errors="ignore")

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


def clean_entire_result(result_path: str):
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for item in data:
        md_path = item["markdown_path"]
        item["content"] = extract_clean_text(md_path)
    
    return data
