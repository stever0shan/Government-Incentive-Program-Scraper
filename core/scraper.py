
import re
import io
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse, unquote
from dateutil.parser import parse
from PyPDF2 import PdfReader
from core.config_loader import ConfigLoader
from core.ai_agent import AIAgent
from langdetect import detect

class DynamicScraper:
    def __init__(self, config_name, output_path):
        self.config_name = config_name
        self.output_path = Path(output_path) if output_path else None
        self.config = ConfigLoader().load(config_name)
        self.results = []
        self.ai = AIAgent()
        self.visited_urls = set()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

        self.pdf_pattern = re.compile(r'\.pdf($|\?)', re.I)
        self.pdf_indicators = ['pdf', 'guidelines', 'form', 'application', 'download']
        self.pdf_min_size = self.config.get("pdf_min_size", 10_000)
        self.pdf_max_size = self.config.get("pdf_max_size", 10_000_000)
        self.auto_pdf = self.config.get("auto_pdf_detection", True)

    def run(self):
        url = self.config["site"]
        print(f"\n Starting scrape: {url}")
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            print(f" Failed to fetch root page: {e}")
            return

        if self.auto_pdf:
            pdf_links = self.detect_pdf_links(soup, url)
            print(f" Found {len(pdf_links)} PDF links")
            for pdf_url in pdf_links:
                if pdf_data := self.process_pdf(pdf_url):
                    self.results.append(pdf_data)

        deep_cfg = self.config.get("deep_links")
        sub_urls = set()

        if isinstance(deep_cfg, dict) and "selector" in deep_cfg:
            elements = soup.select(deep_cfg["selector"])
            for el in elements:
                href = el.get(deep_cfg.get("attribute", "href"))
                if href:
                    full_url = href if href.startswith("http") else requests.compat.urljoin(url, href)
                    sub_urls.add(full_url)
        elif isinstance(deep_cfg, dict) and "urls" in deep_cfg:
            sub_urls.update(deep_cfg["urls"])
        elif isinstance(deep_cfg, list):
            sub_urls.update(deep_cfg)

        print(f" Found {len(sub_urls)} subpages to crawl\n")
        for sub_url in sub_urls:
            self.scrape_page(sub_url)

        if self.output_path:
            self.save()

    def scrape_page(self, page_url):
        if page_url in self.visited_urls:
            return
        self.visited_urls.add(page_url)

        print(f" Scraping subpage: {page_url}")
        try:
            response = self.session.get(page_url, timeout=30)
            response.raise_for_status()

            if "application/pdf" in response.headers.get("Content-Type", ""):
                if pdf_data := self.process_pdf(page_url):
                    self.results.append(pdf_data)
                return

            soup = BeautifulSoup(response.text, "html.parser")

            if self.auto_pdf:
                pdf_links = self.detect_pdf_links(soup, page_url)
                for pdf_url in pdf_links:
                    if pdf_data := self.process_pdf(pdf_url):
                        self.results.append(pdf_data)

            data = self.extract_from_html(soup, page_url)
            self.results.append(data)

        except Exception as e:
            print(f" Failed to scrape {page_url}: {e}")

    def extract_from_html(self, soup, url):
        s = self.config["selectors"]
        raw_text = soup.get_text(" ")
        data = {
            "title": unquote(self.extract_text(soup, s.get("title")) or "N/A"),
            "url": url,
            "funding_amount": self.extract_text(soup, s.get("funding")) or "N/A",
            "deadline": self.extract_deadline(soup, s.get("deadline")) or "N/A",
            "program_type": self.config.get("program_type", "Incentive"),
            "eligibility": self.extract_text(soup, s.get("eligibility")) or "N/A",
            "source_type": "HTML",
            "language": detect(raw_text) if raw_text.strip() else "und"
        }

        if any(self.is_bad(data[k]) for k in ["funding_amount", "deadline", "eligibility"]):
            print(" Falling back to AI extraction due to junk/missing fields...")
            ai_result = self.ai.extract_fields(raw_text)
            for k in ["funding_amount", "deadline", "eligibility"]:
                if self.is_bad(data[k]) and ai_result.get(k):
                    data[k] = ai_result[k].strip()
            print(" GPT response:", ai_result)

        return data

    def detect_pdf_links(self, soup, base_url):
        pdfs = set()
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            text = tag.get_text().lower()
            if self.pdf_pattern.search(href) or any(ind in text for ind in self.pdf_indicators):
                full_url = requests.compat.urljoin(base_url, href)
                if full_url not in self.visited_urls:
                    pdfs.add(full_url)
        return pdfs

    def process_pdf(self, url):
        try:
            if ".pdf" in url and "irs.gov" in url:
                print(f" Skipping broken IRS PDF: {url}")
                return None

            response = self.session.get(url, stream=True, timeout=30)
            size = int(response.headers.get("content-length", 0))
            if size < self.pdf_min_size or size > self.pdf_max_size:
                return None

            with io.BytesIO(response.content) as f:
                reader = PdfReader(f)
                text = "\n".join(page.extract_text() or '' for page in reader.pages)

            if not text.strip():
                raise ValueError("Empty PDF")

            ai_result = self.ai.extract_fields(text)
            return {
                "title": unquote(Path(urlparse(url).path).name),
                "url": url,
                "funding_amount": ai_result.get("funding_amount", "N/A"),
                "deadline": ai_result.get("deadline", "N/A"),
                "program_type": ai_result.get("program_type", self.config.get("program_type", "Document")),
                "eligibility": ai_result.get("eligibility", "N/A"),
                "source_type": "PDF",
                "language": detect(text) if text.strip() else "und"
            }

        except Exception as e:
            print(f"❌ PDF parsing error: {e}")
            bad_dir = Path("bad_pdfs")
            bad_dir.mkdir(exist_ok=True)
            filename = bad_dir / Path(urlparse(url).path).name
            try:
                with open(filename, "wb") as f:
                    f.write(response.content)
            except Exception as save_err:
                print(f" Failed to save bad PDF: {save_err}")
            return None

    def extract_text(self, soup, selector):
        try:
            if not selector:
                return None
            el = soup.select_one(selector)
            return re.sub(r"\s+", " ", el.get_text(strip=True)) if el else None
        except:
            return None

    def extract_deadline(self, soup, selector):
        raw = self.extract_text(soup, selector)
        if not raw:
            return None
        try:
            return parse(raw, fuzzy=True).strftime("%Y-%m-%d")
        except:
            return raw.strip()

    def is_bad(self, val):
        if not val:
            return True
        val = val.strip()
        return val == "N/A" or "PrintShare" in val or "Next Section" in val or len(val) > 2000

    def save(self):
        df = pd.DataFrame(self.results)
        df["title"] = df["title"].apply(lambda x: unquote(x).replace('%20', ' ').strip() if isinstance(x, str) else x)
        df.drop_duplicates(subset="url", inplace=True)
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.output_path, index=False, encoding="utf-8-sig")
        print(f" Saved {len(df)} records to {self.output_path}")
