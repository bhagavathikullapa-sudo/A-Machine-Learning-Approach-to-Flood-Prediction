import json
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

URL = "https://www.oneindia.com/andhra-pradesh-dam-water-level-today-ds5/"

TARGET_DAMS = {
    "Nagarjuna Sagar": "Nagarjuna Sagar",
    "Kalyani Dam": "Tirupati",
    "Srisailam Dam": "Srisailam",
    "Somasila Dam": "Nellore",
    "Prakasam Barrage": "Vijayawada",
}

def scrape_all_dams():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    all_dams = []

    try:
        driver.get(URL)
        time.sleep(8)  # a bit longer

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        tables = soup.find_all("table")
        print("DEBUG tables found:", len(tables))
        if not tables:
            # save page for debugging
            with open("page_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            raise RuntimeError("No dam tables found")

        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if not headers:
                continue
            for row in table.find_all("tr")[1:]:
                tds = row.find_all("td")
                if len(tds) < len(headers):
                    continue
                dam_cell = tds[0]
                dam_link = dam_cell.find("a")
                dam_name = dam_link.get_text(strip=True) if dam_link else dam_cell.get_text(strip=True)
                values = [td.get_text(strip=True) for td in tds]
                dam_data = dict(zip(headers, values))
                dam_data["Dam_Name"] = dam_name
                all_dams.append(dam_data)
        return all_dams
    finally:
        driver.quit()


def build_dam_status_json(all_dams, filename="dam_status.json"):
    result = []
    for dam in all_dams:
        name = dam.get("Dam_Name")
        if name in TARGET_DAMS:
            result.append({
                "Dam_Name": name,
                "City": TARGET_DAMS[name],
                "Current Storage (TMC)": dam.get("Current Storage (TMC)", "N/A"),
                "Current Level (Metre)": dam.get("Current Level (Metre)", "N/A"),
                "Max Storage (TMC)": dam.get("Max Storage (TMC)", "N/A"),
                "Max Level (Metre)": dam.get("Max Level (Metre)", "N/A"),
            })
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(result)} dams to {filename}")

if __name__ == "__main__":
    print("🚀 Scraping dams…")
    dams_data = scrape_all_dams()
    if dams_data:
        build_dam_status_json(dams_data)
        print("\n✅ Scraping and saving completed successfully!")
    else:
        print("❌ Failed to scrape dam data")