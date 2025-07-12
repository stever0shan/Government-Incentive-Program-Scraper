import os
import pandas as pd
from core.scraper import DynamicScraper

CONFIG_FOLDER = "configs"
OUTPUT_FOLDER = "output"
MERGED_FILE = os.path.join(OUTPUT_FOLDER, "all_sites_output.csv")

def main():
    print("🔧 Runner starting...\n")
    all_results = []

    for filename in os.listdir(CONFIG_FOLDER):
        if filename.endswith(".yaml"):
            config_path = os.path.join(CONFIG_FOLDER, filename)
            output_csv = os.path.join(OUTPUT_FOLDER, f"{filename.replace('.yaml', '')}_output.csv")

            print(f" Running: {filename}")
            config_path = os.path.join(CONFIG_FOLDER, filename)
            scraper = DynamicScraper(config_name=config_path, output_path=None)
            scraper.run()

            if scraper.results:
                all_results.extend(scraper.results)
                print(f" Saved: {output_csv} ({len(scraper.results)} entries)\n")
            else:
                print(f" No data found in: {filename}\n")

    if all_results:
        df = pd.DataFrame(all_results)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        df.to_csv(MERGED_FILE, index=False, encoding="utf-8-sig")
        print(f"\n Merged output saved: {MERGED_FILE}")
    else:
        print(" No data extracted from any config.")

if __name__ == "__main__":
    main()
