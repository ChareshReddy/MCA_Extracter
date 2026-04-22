import os
import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests
import threading

def interruptible_sleep(seconds, stop_event):
    """Sleeps for the given duration but checks the stop_event every second."""
    for _ in range(int(seconds)):
        if stop_event and stop_event.is_set():
            return True
        time.sleep(1)
    # Handle the fractional part
    fraction = seconds - int(seconds)
    if fraction > 0:
        time.sleep(fraction)
    return stop_event.is_set() if stop_event else False

# List of all final columns we want to export to the Excel sheet
FIELDS = [
    "CIN", "Company Name", "Date of Incorporation", "Activity",
    "Company Status", "ROC", "Company Category",
    "Company Sub Category", "Class of Company", "Age of Company",
    "Email ID", "Website", "Address", "Authorised Capital", 
    "Paid Up Capital", "Current Directors", "Director DINs"
]

def get_cin_list(input_file):
    """
    Reads the provided Excel file and extracts all CIN numbers.
    It automatically finds which row contains the header 'CIN'.
    """
    try:
        df = pd.read_excel(input_file, header=None)
    except Exception as e:
        print(f"[X] Error reading input file: {e}")
        return []

    # Find the row that contains the 'CIN' header
    header_row = None
    for i, row in df.iterrows():
        if any("CIN" in str(cell).upper() for cell in row):
            header_row = i
            break

    if header_row is None:
        print("[X] Could not find 'CIN' column in input file.")
        return []

    # Set the identified row as the dataframe's columns
    df.columns = df.iloc[header_row]
    df = df[header_row + 1:]

    # Locate the exact column name containing 'CIN'
    cin_col = next((c for c in df.columns if "CIN" in str(c).upper()), None)
    if not cin_col:
        return []

    # Convert the column to a clean list of strings
    cin_list = df[cin_col].dropna().astype(str).str.strip().tolist()
    print(f"[OK] Found {len(cin_list)} CINs to process from input file.")
    return cin_list


def scrape_instafinancials(session, cin):
    """
    Main extraction function for a single CIN.
    It scrapes the main overview page and the directors sub-page.
    """
    print(f"\n[Go] Fetching {cin} from InstaFinancials...")

    # Initialize data dictionary with default 'NA' values
    data = {k: "NA" for k in FIELDS}
    data["CIN"] = cin

    # -------------------------------------------------------------
    # 0. Resolve the Official URL via Search Handler
    # -------------------------------------------------------------
    # The 'a-{cin}' trick is often blocked or redirected. 
    # We hit their internal search handler to get the real slugified URL.
    search_url = f"https://www.instafinancials.com/Handlers/SearchHandler.ashx?term={cin}&type=CIN"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": "https://www.instafinancials.com/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        sr = session.get(search_url, headers=headers, timeout=10)
        search_results = sr.json()
        if search_results and len(search_results) > 0:
            # The handler returns a list of suggestions. We take the first match.
            # Typical format: {"value": "COMPANY NAME", "id": "company/slug-cin"}
            slug = search_results[0].get("id")
            if slug:
                target_url = f"https://www.instafinancials.com/{slug}"
            else:
                target_url = f"https://www.instafinancials.com/company/a-{cin}"
        else:
            # Fallback to the old shortcut if search fails
            target_url = f"https://www.instafinancials.com/company/a-{cin}"
    except Exception as e:
        print(f"[!] Search Resolution Failed for {cin}: {e}. Falling back to shortcut.")
        target_url = f"https://www.instafinancials.com/company/a-{cin}"

    try:
        r = session.get(target_url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"[!] Failed to fetch (Status Code: {r.status_code})")
            return data

        soup = BeautifulSoup(r.text, 'html.parser')
        
        # -------------------------------------------------------------
        # 1. Parse Data from Standard Tables (e.g. Email, Category)
        # -------------------------------------------------------------
        for table in soup.find_all('table'):
            for tr in table.find_all('tr'):
                cells = tr.find_all(['td', 'th'])
                if len(cells) == 4:
                    label1, val1, label2, val2 = [c.get_text(strip=True) for c in cells]
                    if label1 == "Company Category": data["Company Category"] = val1
                    if label2 == "Company Category": data["Company Category"] = val2
                    if label1 in ["Company SubCategory", "Company Sub Category"]: data["Company Sub Category"] = val1
                    if label2 in ["Company SubCategory", "Company Sub Category"]: data["Company Sub Category"] = val2
                    if label1 == "Company Class": data["Class of Company"] = val1
                    if label2 == "Company Class": data["Class of Company"] = val2
                    if label1 == "Email ID": data["Email ID"] = val1
                    if label2 == "Email ID": data["Email ID"] = val2
                    if label1 == "Website": data["Website"] = val1
                    if label2 == "Website": data["Website"] = val2
                elif len(cells) == 2:
                    label, val = cells[0].get_text(strip=True), cells[1].get_text(strip=True)
                    if label == "Company Category": data["Company Category"] = val
                    if label in ["Company SubCategory", "Company Sub Category"]: data["Company Sub Category"] = val
                    if label == "Company Class": data["Class of Company"] = val
                    if label == "Email ID": data["Email ID"] = val
                    if label == "Website": data["Website"] = val
                elif len(cells) >= 2:
                    label, val = cells[0].get_text(strip=True), cells[1].get_text(strip=True)
                    if label == "Address": data["Address"] = val

        # -------------------------------------------------------------
        # 2. Parse Overview Paragraph for Contextual Details via Regex
        # -------------------------------------------------------------
        overview_p = soup.select_one('#companyOverviewContainer p')
        if overview_p:
            # Replace the Rupee symbol with 'INR ' to avoid terminal encoding crashes
            overview = overview_p.get_text().replace('\u20b9', 'INR ')
            
            # Extract Company Name (Everything before " is a ")
            name_match = re.search(r"^(.*?) is a ", overview)
            if name_match: data["Company Name"] = name_match.group(1).strip()
            
            # Extract Age of Company
            age_match = re.search(r"is a (.*?) Years old", overview)
            if age_match: data["Age of Company"] = age_match.group(1).strip() + " Years"
            
            # Extract Date of Incorporation
            doi_match = re.search(r"incorporated on (\d{2} [A-Za-z]+ \d{4})", overview)
            if doi_match: data["Date of Incorporation"] = doi_match.group(1).strip()
            
            # Extract Company Status
            stat_match = re.search(r"status of the company is (.*?)\.", overview)
            if stat_match: data["Company Status"] = stat_match.group(1).strip()
            
            # Extract Main Line of Business / Activity
            act_match = re.search(r"business is (.*?)$", overview)
            if act_match: data["Activity"] = act_match.group(1).strip()
            
            # Extract Authorised Capital
            auth_match = re.search(r'authorized share capital is (.*?) and', overview)
            if auth_match: data["Authorised Capital"] = auth_match.group(1).strip()
            
            # Extract Paid up Capital
            paid_match = re.search(r'paid up capital is (.*?)(?:\. As|As) per MCA', overview)
            if paid_match: data["Paid Up Capital"] = paid_match.group(1).strip()
            # Regex Fallback if standard regex didn't catch the Paid Up capital formatting
            if data["Paid Up Capital"] == "NA":
                paid_match_2 = re.search(r'paid up capital is (.*?)\.', overview)
                if paid_match_2: data["Paid Up Capital"] = paid_match_2.group(1).strip()

        # -------------------------------------------------------------
        # 3. Parse alternate paragraphs for missing ROC (Registrar of Companies)
        # -------------------------------------------------------------
        for p in soup.find_all('p'):
            p_text = p.get_text()
            if "is registered at" in p_text and data["ROC"] == "NA":
                roc_match = re.search(r"is registered at (.*?)\.", p_text)
                if roc_match: data["ROC"] = roc_match.group(1).strip()
                
        # -------------------------------------------------------------
        # 4. Secondary Request to fetch Directors Page
        # -------------------------------------------------------------
        if data["Company Name"] != "NA":
            try:
                # Directors are hosted on a separate URL suffix
                dir_url = f"https://www.instafinancials.com/company/a-{cin}/company-directors"
                r_dir = session.get(dir_url, timeout=15)
                
                if r_dir.status_code == 200:
                    soup_dir = BeautifulSoup(r_dir.text, 'html.parser')
                    directors = []
                    dins = []
                    
                    # Look through the director tables
                    for tr in soup_dir.find_all('tr'):
                        cells = tr.find_all(['td', 'th'])
                        # If row has director info (not headers or empty cells)
                        if len(cells) >= 3 and cells[0].get_text(strip=True) not in ["Director Name", "Signatory Name"]:
                            name = cells[0].get_text(strip=True)
                            din = cells[1].get_text(strip=True)
                            # Verify DIN looks like a real ID
                            if din.isdigit() and len(din) >= 5:
                                directors.append(name)
                                dins.append(din)
                                
                    # Join the lists with commas for Excel formatting
                    if directors: data["Current Directors"] = ", ".join(directors)
                    if dins: data["Director DINs"] = ", ".join(dins)
            except Exception as e:
                print(f"[!] Warning: Could not fetch directors for {cin}: {e}")
        
        # -------------------------------------------------------------
        # 5. Verify extraction success and check for Web Application Firewall (WAF) blocks
        # -------------------------------------------------------------
        if data["Company Name"] == "NA":
            # If the name is NA, it means we either hit a Cloudflare block or the page doesn't exist
            title = soup.title.get_text(strip=True) if soup.title else "No Title"
            print(f"[!] Blocked or Missing! Page Title: {title}")
            raise Exception("WAF_Block")
        else:
             print(f"[V] Successfully extracted details for {data.get('Company Name', cin)[:30]}")

        return data

    except Exception as e:
         if str(e) == "WAF_Block":
             raise e
         print(f"[X] Request Error for {cin}: {e}")
         # Treat raw network/connection errors identically to WAF blocks to trigger the retry loop
         raise Exception("WAF_Block") 


def run(input_file=None, output_file=None, delay_range=(30, 300), log_callback=None, stop_event=None):
    """
    Main Execution Engine. Handles interactive CLI setup, session management,
    and the core iterative scraping loop with anti-bot delays.
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    log("="*60)
    log("      INSTAFINANCIALS HIGH-VOLUME DATA SCRAPER      ")
    log("="*60)

    # Ask user for input path if not provided
    if input_file is None:
        input_file = input("\nEnter the path to your input Excel file [default: input/companies.xlsx]:\n> ").strip()
        if not input_file:
            input_file = "input/companies.xlsx"

    if not os.path.exists(input_file):
        log(f"\n[X] Error: Could not find '{input_file}'. Please check the path and try again.")
        return

    # Ask user for output path if not provided
    if output_file is None:
        output_file = input("\nEnter the path to save the output Excel file [default: output/Pankaj_Vikram_Extracted_data.xlsx]:\n> ").strip()
        if not output_file:
            output_file = "output/Pankaj_Vikram_Extracted_data.xlsx"
        
    # Ensure the directory structure exists before writing
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    log("\n[OK] Starting scraper engine...\n")
    results = []

    # To pass the log callback inside
    def custom_print(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    # We need to temporarily patch print in get_cin_list and scrape_instafinancials, 
    # but since they are global, we'll just redefine print locally if needed, 
    # or pass a status callback. Actually, let's just let stdout be captured by the API.
    # We will use sys.stdout redirection in the API instead of modifying every print.
    # So we'll just leave the rest of the file as is, but we'll use the delay_range.

    cin_list = get_cin_list(input_file)
    if not cin_list:
        return

    # curl_cffi perfectly mimics Chrome TLS handshakes, naturally bypassing basic Cloudflare tests
    session = requests.Session(impersonate="chrome110")

    for i, cin in enumerate(cin_list, start=1):
        if stop_event and stop_event.is_set():
            log("\n[!] Stop signal received. Terminating scrape...")
            break
            
        attempts = 0
        
        # Retry loop for auto-healing if we get blocked
        while attempts < 3:
            try:
                data = scrape_instafinancials(session, cin)
                results.append(data)
                break
            except Exception as e:
                attempts += 1
                if attempts < 3:
                    print(f"[Refresh] WAF Block detected. Pausing for 30 seconds to cooldown... (Attempt {attempts}/3)")
                    if interruptible_sleep(30, stop_event):
                        break
                    # Recreate session to clear any potential IP/cookie tracking from the firewall
                    session = requests.Session(impersonate="chrome110")
                else:
                    print(f"[X] Failed to fetch {cin} after 3 attempts. Skipping.")
                    results.append({"CIN": cin, "Company Name": "NA"})
                    break

        # Save partial progress constantly to prevent data loss
        pd.DataFrame(results).to_excel(output_file, index=False)
        print(f"[Save] Autosaved ({i}/{len(cin_list)})")
            
        # Professional delay model to bypass WAF
        import random
        delay = random.uniform(delay_range[0], delay_range[1])
        print(f"[Wait] Sleeping for {int(delay)} seconds to emulate human reading...")
        if interruptible_sleep(delay, stop_event):
            log("\n[!] Stop signal received during sleep. Terminating.")
            break

    pd.DataFrame(results).to_excel(output_file, index=False)
    print(f"\n[OK] SCRAPE COMPLETE - FINAL SAVED TO {output_file}")

if __name__ == "__main__":
    run()
