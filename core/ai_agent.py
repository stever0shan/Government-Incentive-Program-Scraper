import openai
import os
import json
import re

#  Set API key from environment or directly 
openai.api_key = "sk-...your_key_here..."

class AIAgent:
    def __init__(self):
        pass

    def extract_fields(self, raw_text):
        prompt = f"""
You're an AI assistant that extracts structured information from webpages about funding programs.

Please read the following text and extract these three fields:

1. "funding_amount": What kind of funding is being offered? Include specific dollar amounts (like "$3,200"), percentages (like "30%"), or types (like "grants", "tax credits").
2. "deadline": Mention any date or time period to apply.
3. "eligibility": Who can apply or qualify?

TEXT:
{raw_text[:5000]}

Return ONLY valid JSON in this format:

{{
  "funding_amount": "...",
  "deadline": "...",
  "eligibility": "..."
}}
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = response.choices[0].message["content"].strip()
            print(" GPT response:", content)

            result = json.loads(content) if content.startswith("{") else {}

            # Post-cleaning funding_amount for $/%, etc.
            funding = result.get("funding_amount", "N/A")
            matches = re.findall(r'(\$\d{1,3}(,\d{3})*(\.\d+)?|\d+%|\d+ percent)', funding, re.IGNORECASE)
            if matches:
                funding = matches[0][0]  # Use only the first clean match

            return {
                "funding_amount": funding or "N/A",
                "deadline": result.get("deadline", "N/A"),
                "eligibility": result.get("eligibility", "N/A")
            }

        except Exception as e:
            print(f"⚠️ AI Extraction failed: {e}")
            return {
                "funding_amount": "N/A",
                "deadline": "N/A",
                "eligibility": "N/A"
            }