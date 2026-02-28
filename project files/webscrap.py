import json
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

URL = "https://www.oneindia.com/andhra-pradesh-dam-water-level-today-ds5/"

def scrape_all_dams():
    """Scrape all dam data from the page"""
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
        time.sleep(5)  # Wait for page to fully load

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Find all tables on the page
        tables = soup.find_all("table")
        
        if not tables:
            raise RuntimeError("No dam tables found")

        print(f"Found {len(tables)} table(s) on the page\n")

        # Process each table
        for table_index, table in enumerate(tables):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            
            if not headers:
                continue

            print(f"Table {table_index + 1} Headers: {headers}")
            
            rows = table.find_all("tr")[1:]  # Skip header row
            
            for row in rows:
                tds = row.find_all("td")
                if not tds or len(tds) < len(headers):
                    continue
                
                # Extract dam name (from link text if available, else direct text)
                dam_cell = tds[0]
                dam_link = dam_cell.find("a")
                dam_name = dam_link.get_text(strip=True) if dam_link else dam_cell.get_text(strip=True)
                
                # Extract all values
                values = [td.get_text(strip=True) for td in tds]
                
                # Create dictionary with headers as keys
                dam_data = dict(zip(headers, values))
                dam_data['Dam_Name'] = dam_name
                
                all_dams.append(dam_data)
                
                print(f"  ✓ {dam_name}: {dam_data.get('Current Storage (TMC)', 'N/A')} TMC")

        print(f"\n✅ Total dams scraped: {len(all_dams)}\n")
        return all_dams

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        return []
    finally:
        driver.quit()


def save_to_csv(data, filename="all_dams_data.csv"):
    """Save dam data to CSV file"""
    if not data:
        print("No data to save")
        return
    
    keys = data[0].keys()
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ Data saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")


def save_to_json(data, filename="all_dams_data.json"):
    """Save dam data to JSON file"""
    if not data:
        print("No data to save")
        return
    
    try:
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        print(f"✅ Data saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")


def save_to_txt(data, filename="all_dams_data.txt"):
    """Save dam data to readable text file"""
    if not data:
        print("No data to save")
        return
    
    try:
        with open(filename, 'w', encoding='utf-8') as txtfile:
            txtfile.write("="*80 + "\n")
            txtfile.write("ANDHRA PRADESH DAM WATER LEVEL DATA\n")
            txtfile.write(f"Date: 9th December 2025\n")
            txtfile.write("="*80 + "\n\n")
            
            for i, dam in enumerate(data, 1):
                txtfile.write(f"{i}. Dam Name: {dam.get('Dam_Name', 'N/A')}\n")
                txtfile.write(f"   Current Storage (TMC): {dam.get('Current Storage (TMC)', 'N/A')}\n")
                txtfile.write(f"   Current Level (Metre): {dam.get('Current Level (Metre)', 'N/A')}\n")
                txtfile.write(f"   Max Storage (TMC): {dam.get('Max Storage (TMC)', 'N/A')}\n")
                txtfile.write(f"   Max Level (Metre): {dam.get('Max Level (Metre)', 'N/A')}\n")
                txtfile.write("-"*80 + "\n\n")
        
        print(f"✅ Data saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving TXT: {e}")

# ---- NEW: build small dam_status.json for Flask ----

TARGET_DAMS = {
    "Nagarjuna Sagar": "Nagarjuna Sagar",
    "Kalyani Dam": "Tirupati",
    "Srisailam Dam": "Srisailam",
    "Somasila Dam": "Nellore",
    "Prakasam Barrage": "Vijayawada",
}

def build_dam_status_json(all_dams, filename="dam_status.json"):
    """Create compact JSON with only selected dams and key fields."""
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
    if result:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(result)} dams to {filename}")
    else:
        print("❌ No target dams found in scraped data")

if __name__ == "__main__":
    print("🚀 Starting web scraping...\n")
    
    # Scrape all dam data
    dams_data = scrape_all_dams()
    
    if dams_data:
        print("\n📊 Saving data in multiple formats...\n")
        
        # Save in all formats
        save_to_csv(dams_data)
        save_to_json(dams_data)
        save_to_txt(dams_data)
        
        print("\n✅ Scraping and saving completed successfully!")
        
        # Print sample data
        print("\n📋 Sample data (first 3 dams):")
        for dam in dams_data[:3]:
            print(f"\n  {dam}")
    else:
        print("❌ Failed to scrape dam data")
