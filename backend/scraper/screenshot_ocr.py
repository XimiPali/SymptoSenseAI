"""
scraper/screenshot_ocr.py
--------------------------
Screenshot + OCR ETL stage — additional pipeline step after frequency analysis.

For each clean URL (capped at max_urls to keep response times reasonable):
  1. Open URL in headless Chrome via Selenium
  2. Capture a full-page screenshot → backend/screenshots/<hash>.png
  3. Run pytesseract OCR on the image → extract visible text
  4. Persist results to ocr_results table (FK → search_results.id)

System requirements (must be installed separately):
  - Google Chrome browser
  - Tesseract-OCR:
      Windows: https://github.com/UB-Mannheim/tesseract/wiki
      After install, add Tesseract to PATH or set pytesseract.pytesseract.tesseract_cmd

Python packages (see requirements.txt):
  pip install selenium webdriver-manager pytesseract Pillow
"""

import hashlib
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from scraper.scraper_db import OcrResult, SearchResult

# ── Screenshot output directory ────────────────────────────────────────────
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

PAGE_LOAD_TIMEOUT = 15   # seconds before giving up on a page
MAX_URLS_DEFAULT  = 5    # kept low — each page can take 3-15 s


# ── Optional dependency guards ─────────────────────────────────────────────

def _import_selenium():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        return webdriver, Options, Service, ChromeDriverManager
    except ImportError:
        return None, None, None, None


def _import_ocr():
    try:
        import pytesseract
        from PIL import Image
        return pytesseract, Image
    except ImportError:
        return None, None


# ── Internal helpers ───────────────────────────────────────────────────────

def _url_hash(url: str) -> str:
    """Short deterministic filename derived from the URL."""
    return hashlib.md5(url.encode()).hexdigest()[:14]


def _make_driver(webdriver, Options, Service, ChromeDriverManager):
    """Return a headless Chrome WebDriver instance."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-extensions")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def _take_screenshot(driver, url: str) -> Optional[Path]:
    """Navigate to *url* and save a screenshot. Returns the Path or None."""
    try:
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.get(url)
        out = SCREENSHOT_DIR / f"{_url_hash(url)}.png"
        driver.save_screenshot(str(out))
        print(f"[ocr] screenshot saved: {out.name}  ({url[:60]})")
        return out
    except Exception as exc:
        print(f"[ocr] screenshot FAILED for {url[:60]}: {exc}")
        return None


def _run_ocr(pytesseract, Image, image_path: Path) -> str:
    """Run Tesseract OCR on *image_path*. Returns extracted text."""
    try:
        img  = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        print(f"[ocr] OCR extracted: {len(text):,} chars  ({image_path.name})")
        return text
    except Exception as exc:
        print(f"[ocr] OCR FAILED for {image_path.name}: {exc}")
        return ""


# ── Public API ─────────────────────────────────────────────────────────────

def run_screenshot_ocr(
    db:       Session,
    urls:     List[str],
    term_id:  int,
    max_urls: int = MAX_URLS_DEFAULT,
) -> None:
    """
    Additional ETL stage: screenshot + OCR for the first *max_urls* clean URLs.

    Runs sequentially (one Chrome tab at a time) to avoid memory exhaustion.
    Results are written to ocr_results with a FK to search_results.

    Gracefully skips if Selenium or pytesseract are not installed.
    """
    webdriver, Options, Service, ChromeDriverManager = _import_selenium()
    pytesseract, Image = _import_ocr()

    if webdriver is None:
        print("[ocr] SKIP — selenium / webdriver-manager not installed")
        print("[ocr]   run: pip install selenium webdriver-manager")
        return

    if pytesseract is None:
        print("[ocr] SKIP — pytesseract / Pillow not installed")
        print("[ocr]   run: pip install pytesseract Pillow")
        print("[ocr]   also install Tesseract-OCR: https://github.com/UB-Mannheim/tesseract/wiki")
        return

    targets = urls[:max_urls]
    if not targets:
        return

    print(f"[ocr] starting screenshot+OCR for {len(targets)} URL(s) → {SCREENSHOT_DIR}")
    driver = _make_driver(webdriver, Options, Service, ChromeDriverManager)

    try:
        for url in targets:
            # Resolve FK: find the matching raw search_results row
            sr = (
                db.query(SearchResult)
                .filter(
                    SearchResult.term_id == term_id,
                    SearchResult.url     == url,
                )
                .first()
            )
            search_result_id = sr.id if sr else None

            img_path = _take_screenshot(driver, url)

            if img_path:
                ocr_text = _run_ocr(pytesseract, Image, img_path)
            else:
                ocr_text = ""

            record = OcrResult(
                search_result_id = search_result_id,
                url              = url,
                screenshot_path  = str(img_path) if img_path else None,
                ocr_text         = ocr_text[:10_000],   # cap stored text at 10k chars
                word_count       = len(ocr_text.split()) if ocr_text else 0,
            )
            db.add(record)
            db.commit()

    finally:
        driver.quit()
        print(f"[ocr] done — Chrome closed")
