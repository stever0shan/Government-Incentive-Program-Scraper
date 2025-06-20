# 🏛️ Government Incentive Program Scraper

An AI-enhanced, multilingual web scraper built to extract and standardize funding opportunity data — including grants, tax credits, and rebate programs — from U.S. government and affiliated sites like NYSERDA, EPA, DOE, IRS, DSIRE, HUD, and more.

---

## 🔍 Features

- ✅ **Dynamic Website Scraping** using YAML config files  
- 📄 **PDF & HTML Extraction** with fallback to OpenAI GPT  
- 🌎 **Language Detection** for multilingual government sites  
- 🧠 **AI Extraction Engine** to fill in missing fields  
- 🧼 **Smart Cleaning**: 
  - Deduplicates entries
  - Normalizes `%20` and unicode artifacts
  - Classifies funding types, amounts, and deadlines

---

## 📦 Output Format (CSV)

Each row in the final dataset includes:

| Column           | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `title`          | Title of the funding opportunity (cleaned)                                 |
| `url`            | Source URL                                                                  |
| `funding_amount` | Normalized amount (e.g., `$3,200`, `30%`, or `Tax Credit`)                 |
| `deadline`       | Application deadline (standardized or best-effort parsed)                  |
| `program_type`   | Type of program (e.g., `Grant`, `Tax Credit`, `Environmental Incentive`)   |
| `eligibility`    | Who can apply (e.g., `nonprofits`, `tribes`, `CDEs`, etc.)                 |
| `source_type`    | `HTML` or `PDF`                                                             |
| `language`       | ISO language code (e.g., `en`, `es`, `ko`, `zh-hant`)                      |

---

## 🛠️ Installation

```bash
git clone https://github.com/your-username/government-incentive-scraper.git
cd government-incentive-scraper

# (Recommended) Set up a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Eun the scraper on a specific government source using its YAML config file:
python runner.py --config configs/epa.yaml --output outputs/epa_results.csv

# YAML Config Example
# Each target site is configured via a simple .yaml file like:
site: https://www.epa.gov/greenhouse-gas-reduction-fund

program_type: Environmental Incentive

selectors:
  title: "h1.page-title"
  funding: ".field--name-body"
  deadline: ".field--name-deadline"
  eligibility: ".eligibility-section"

deep_links:
  selector: "a[href*='/greenhouse-gas-reduction-fund']"
  attribute: "href"

auto_pdf_detection: true
pdf_min_size: 10000
pdf_max_size: 10000000

Add your OpenAI API key directly in ai_agent.py:
export OPENAI_API_KEY=sk-xxxxxxxx  # or use .env if preferred
