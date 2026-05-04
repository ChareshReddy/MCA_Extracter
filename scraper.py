import os
import time
import re
import datetime
import random
import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests
import threading
import config
import logging
from logging.handlers import RotatingFileHandler

# Use the centralized logger configured in api.py
logger = logging.getLogger(__name__)

def interruptible_sleep(seconds, stop_event):
    """Sleeps for the given duration but checks the stop_event every second."""
    for i in range(int(seconds), 0, -1):
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

def get_input_data(input_file):
    """
    Reads the provided Excel file and identifies the CIN column and relevant rows.
    Returns (dataframe, cin_column_name, header_row_index)
    """
    try:
        df = pd.read_excel(input_file, header=None)
    except Exception as e:
        print(f"[X] Error reading input file: {e}")
        return None, None, None

    # Find the row that contains the 'CIN' header
    header_row = None
    for i, row in df.iterrows():
        if any("CIN" in str(cell).upper() for cell in row):
            header_row = i
            break

    if header_row is None:
        print("[X] Could not find 'CIN' column in input file.")
        return None, None, None

    # Set the identified row as the dataframe's columns
    df.columns = df.iloc[header_row]
    # We keep the whole DF but we'll work with the part below header_row
    return df, header_row


def scrape_mca_data(session, cin, log_callback=None):
    """
    Main extraction function for a single CIN.
    It scrapes the main overview page and the directors sub-page.
    """
    # Redundant validation safety
    is_valid_cin = len(cin) == 21 and cin[0].upper() in ['U', 'L']
    is_valid_llpin = len(cin) == 7
    if not (is_valid_cin or is_valid_llpin):
        return {"CIN": cin, "Company Name": "NA", "Status": "Incorrect Format"}

    if log_callback:
        logger.info(f"Fetching {cin} from MCA...")
        log_callback(f"[Go] Fetching {cin} from MCA...")
    else:
        logger.info(f"Fetching {cin} from MCA...")

    # Initialize data dictionary with default 'NA' values
    data = {k: "NA" for k in FIELDS}
    data["CIN"] = cin

    # -------------------------------------------------------------
    # 0. Resolve the Official URL via Search Handler
    # -------------------------------------------------------------
    # The 'a-{cin}' trick is often blocked or redirected. 
    # We hit their internal search handler to get the real slugified URL.
    search_url = f"{config.SEARCH_HANDLER_URL}?term={cin}&type=CIN"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": f"{config.BASE_URL}/",
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
                target_url = f"{config.BASE_URL}/{slug}"
            else:
                target_url = f"{config.BASE_URL}/company/a-{cin}"
        else:
            # Fallback to the old shortcut if search fails
            target_url = f"{config.BASE_URL}/company/a-{cin}"
    except Exception:
        # Silently fall back to the shortcut URL if search resolution fails
        target_url = f"{config.BASE_URL}/company/a-{cin}"

    try:
        r = session.get(target_url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.error(f"Failed to fetch {cin} (Status Code: {r.status_code})")
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
                dir_url = f"{config.BASE_URL}/company/a-{cin}/company-directors"
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


def run(input_file=None, output_file=None, delay_range=None, log_callback=None, stop_event=None, progress_callback=None, total=0, pending=0):
    """
    Main Execution Engine. Handles status tracking, record limits, and incremental saving.
    """
    if delay_range is None:
        delay_range = (config.DELAY_MIN_SECONDS, config.DELAY_MAX_SECONDS)
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    def update_progress(current, total):
        if progress_callback:
            progress_callback(current, total)

    log("="*60)
    log("      MCA HIGH-VOLUME DATA EXTRACTION ENGINE      ")
    log("="*60)

    if input_file is None or not os.path.exists(input_file):
        log(f"\n[X] Error: Input file not found.")
        return

    log("\n[OK] Starting scraper engine...\n")
    
    df_full, header_row = get_input_data(input_file)
    if df_full is None:
        return

    # Identify CIN column
    cin_col = next((c for c in df_full.columns if "CIN" in str(c).upper()), None)
    if not cin_col:
        log("[X] CIN column not found.")
        return

    # Add Status and Extracted Time columns if they don't exist
    if 'Status' not in df_full.columns:
        df_full['Status'] = ""
        df_full.at[header_row, 'Status'] = "Status"
    if 'Extracted Time' not in df_full.columns:
        df_full['Extracted Time'] = ""
        df_full.at[header_row, 'Extracted Time'] = "Extracted Time"

    # Records to process are those below header_row
    data_rows = df_full.index[header_row + 1:]
    total_records = len(data_rows)
    
    if total_records > config.MAX_RECORDS_PER_FILE:
        log(f"[X] Error: File contains {total_records} records. Please add a file with less than {config.MAX_RECORDS_PER_FILE} records.")
        return

    log(f"[OK] Total CINs found: {total_records}")

    # Results for the output file
    results = []
    # If output file exists, maybe load existing results? 
    # The user said "data automatically store in the output xlsx file".
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_excel(output_file)
            results = existing_df.to_dict('records')
            log(f"[Info] Loaded {len(results)} existing records from output file.")
        except:
            pass

    session = requests.Session(impersonate="chrome110")
    processed_count = 0
    update_progress(0, total_records)

    for idx in data_rows:
        if stop_event and stop_event.is_set():
            log("\n[!] Stop signal received. Terminating scrape...")
            break

        cin = str(df_full.at[idx, cin_col]).strip()
        if not cin or cin == "nan":
            continue

        # Validation Logic: CIN (21 chars, starts with U/L) or LLPIN (7 chars)
        is_valid_cin = len(cin) == 21 and cin[0].upper() in ['U', 'L']
        is_valid_llpin = len(cin) == 7
        
        if not (is_valid_cin or is_valid_llpin):
            log(f"[Skip] '{cin}' -> Incorrect Format")
            df_full.at[idx, 'Status'] = "Incorrect Format"
            df_full.at[idx, 'Extracted Time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                df_full.to_excel(input_file, index=False, header=False)
                processed_count += 1
                update_progress(processed_count, total_records)
            except: pass
            continue

        # Double check: Is it already done?
        status = str(df_full.at[idx, 'Status']).strip()
        if status == "Exported":
            continue

        attempts = 0
        success = False
        extracted_data = None

        while attempts < 3:
            try:
                extracted_data = scrape_mca_data(session, cin, log_callback=log)
                success = True
                break
            except Exception as e:
                attempts += 1
                if attempts < 3:
                    logger.warning(f"WAF Block detected for {cin}. Pausing for 30 seconds... (Attempt {attempts}/3)")
                    log(f"[Refresh] WAF Block detected. Pausing for 30 seconds... (Attempt {attempts}/3)")
                    if interruptible_sleep(30, stop_event):
                        break
                    session = requests.Session(impersonate="chrome110")
                else:
                    logger.error(f"Failed to fetch {cin} after 3 attempts.")
                    log(f"[X] Failed to fetch {cin} after 3 attempts.")
                    break
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if success and extracted_data and extracted_data.get("Company Name") != "NA":
            df_full.at[idx, 'Status'] = "Exported"
            df_full.at[idx, 'Extracted Time'] = current_time
            results.append(extracted_data)
            logger.info(f"Successfully exported {cin}")
            log(f"[Save] {cin} -> Exported")
        else:
            df_full.at[idx, 'Status'] = "Extraction Failed"
            df_full.at[idx, 'Extracted Time'] = current_time
            logger.error(f"Failed to export {cin} (Extraction Failed)")
            log(f"[Fail] {cin} -> Extraction Failed")

        # Save both files incrementally
        try:
            # Save Input File (Status update)
            # We save the whole thing including headers above header_row
            # To preserve original formatting as much as possible, we just write the DF
            df_full.to_excel(input_file, index=False, header=False)
            
            # Save Output File
            pd.DataFrame(results).to_excel(output_file, index=False)
            processed_count += 1
            update_progress(processed_count, total_records)
        except Exception as e:
            logger.error(f"File Save Error: {e}")
            log(f"[!] Warning: Could not save files (maybe they are open in Excel?): {e}")

        # Random delay between delay_min and delay_max seconds
        delay = random.uniform(delay_range[0], delay_range[1])
        logger.info(f"Sleeping for {int(delay)}s...")
        log(f"[Wait] Next extraction in {int(delay)}s...")
        if interruptible_sleep(delay, stop_event):
            break

    log(f"\n[OK] SCRAPE PROCESS FINISHED.")

if __name__ == "__main__":
    # For testing purposes only
    run()
