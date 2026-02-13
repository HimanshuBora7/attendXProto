"""
Utility functions for web scraping attendance data
"""
import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By


def find_and_expand_tree_node(driver, text_keywords, frame_names=['data', 'top', 'contents', 'bottom', 'banner']):
    """Find a tree node and click its expandable hitarea to expand it"""
    print(f"🔍 Looking for expandable tree node containing: {text_keywords}")
    
    for frame_name in frame_names:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame_name)
            
            # Strategy 1: Find by looking for text near hitarea
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Attendance') or contains(text(), 'ATTENDANCE')]")
            
            for elem in elements:
                try:
                    parent = elem.find_element(By.XPATH, "./..")
                    hitareas = parent.find_elements(By.CLASS_NAME, "hitarea")
                    
                    for hitarea in hitareas:
                        classes = hitarea.get_attribute("class") or ""
                        if "expandable-hitarea" in classes or "collapsable-hitarea" in classes:
                            print(f"✅ Found expandable tree node in '{frame_name}' frame!")
                            hitarea.click()
                            time.sleep(2)
                            driver.switch_to.default_content()
                            return True
                except:
                    continue
            
            # Strategy 2: Find all hitareas and click the expandable ones
            hitareas = driver.find_elements(By.CLASS_NAME, "hitarea")
            
            for hitarea in hitareas:
                classes = hitarea.get_attribute("class") or ""
                
                if "expandable-hitarea" in classes:
                    try:
                        parent = hitarea.find_element(By.XPATH, "./..")
                        text = parent.text.strip()
                        
                        if any(keyword.lower() in text.lower() for keyword in text_keywords):
                            print(f"✅ Found expandable '{text}' in '{frame_name}' frame!")
                            hitarea.click()
                            time.sleep(2)
                            driver.switch_to.default_content()
                            return True
                    except:
                        continue
                        
        except Exception as e:
            continue
    
    driver.switch_to.default_content()
    return False


def find_and_click_link(driver, keywords, frame_names=['data', 'top', 'contents', 'bottom', 'banner'], exact_match=False):
    """Helper to find and click a link across multiple frames"""
    try:
        driver.switch_to.default_content()
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            link_text = link.text.strip()
            link_html = link.get_attribute('innerHTML') or ""
            
            if exact_match:
                if link_text in keywords or any(keyword in link_html for keyword in keywords):
                    print(f"✅ Found '{link.text}' in main content!")
                    link.click()
                    return True
            else:
                if any(keyword.lower() in link_text.lower() for keyword in keywords):
                    print(f"✅ Found '{link.text}' in main content!")
                    link.click()
                    return True
    except Exception as e:
        pass
    
    for frame_name in frame_names:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame_name)
            
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                link_text = link.text.strip()
                link_html = link.get_attribute('innerHTML') or ""
                
                if exact_match:
                    if link_text in keywords or any(keyword in link_html for keyword in keywords):
                        print(f"✅ Found '{link.text}' in {frame_name}!")
                        link.click()
                        return True
                else:
                    if any(keyword.lower() in link_text.lower() for keyword in keywords):
                        print(f"✅ Found '{link.text}' in {frame_name}!")
                        link.click()
                        return True
        except Exception as e:
            continue
    return False


def extract_attendance_table_enhanced(html, debug=False):
    """
    Enhanced attendance table parser
    Handles the specific HTML format from NSIT IMS portal
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    if debug:
        print("\n" + "="*80)
        print("🔍 DEBUG: Analyzing HTML structure")
        print("="*80)
    
    # Find all tables
    tables = soup.find_all('table')
    if debug:
        print(f"\n📊 Found {len(tables)} table(s) in HTML")
    
    attendance_data = []
    
    for table_idx, table in enumerate(tables):
        if debug:
            print(f"\n--- Analyzing Table {table_idx + 1} ---")
        
        rows = table.find_all('tr')
        
        # Find header row with subject codes (looks for pattern like "ITITC601")
        subject_codes = []
        header_row_idx = -1
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Look for row with subject codes
            has_subject_codes = any(
                bool(re.match(r'^[A-Z]{2,4}\d{4}$', text)) 
                for text in cell_texts
            )
            
            if has_subject_codes:
                header_row_idx = row_idx
                # Extract subject codes (skip first column which is usually "Days")
                for cell_text in cell_texts[1:]:
                    if re.match(r'^[A-Z]{2,4}\d{4}$', cell_text):
                        subject_codes.append(cell_text)
                
                if debug:
                    print(f"✅ Found subject codes: {subject_codes}")
                break
        
        if not subject_codes:
            if debug:
                print("⚠️ No subject codes found")
            continue
        
        # Now find the "Overall" rows
        overall_class_row = None
        overall_absent_row = None
        overall_present_row = None
        overall_percent_row = None
        
        for row_idx in range(header_row_idx + 1, len(rows)):
            row = rows[row_idx]
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
                
            first_cell = cells[0].get_text(strip=True).lower()
            
            if 'overall class' in first_cell or 'overall' in first_cell and 'class' in first_cell:
                overall_class_row = [cell.get_text(strip=True) for cell in cells]
            elif 'overall' in first_cell and 'absent' in first_cell:
                overall_absent_row = [cell.get_text(strip=True) for cell in cells]
            elif 'overall' in first_cell and 'present' in first_cell:
                overall_present_row = [cell.get_text(strip=True) for cell in cells]
            elif 'overall' in first_cell and '%' in first_cell or 'overall (%)' in first_cell:
                overall_percent_row = [cell.get_text(strip=True) for cell in cells]
        
        # Extract data for each subject
        if overall_class_row and overall_absent_row and overall_present_row:
            if debug:
                print(f"✅ Found overall rows")
            
            for idx, subject_code in enumerate(subject_codes):
                try:
                    # Index in row is idx + 1 (skip first column)
                    cell_idx = idx + 1
                    
                    total_classes = int(overall_class_row[cell_idx]) if cell_idx < len(overall_class_row) else 0
                    absent = int(overall_absent_row[cell_idx]) if cell_idx < len(overall_absent_row) else 0
                    present = int(overall_present_row[cell_idx]) if cell_idx < len(overall_present_row) else 0
                    
                    # Get percentage if available
                    if overall_percent_row and cell_idx < len(overall_percent_row):
                        percent_str = overall_percent_row[cell_idx].replace('%', '').strip()
                        try:
                            percentage = float(percent_str)
                        except:
                            percentage = round((present / total_classes * 100), 2) if total_classes > 0 else 0
                    else:
                        percentage = round((present / total_classes * 100), 2) if total_classes > 0 else 0
                    
                    attendance_data.append({
                        'Subject Code': subject_code,
                        'Subject Name': subject_code,  # We don't have names in this format
                        'Classes Present': present,
                        'Classes Absent': absent,
                        'Total Classes': total_classes,
                        'Attendance %': percentage
                    })
                    
                    if debug:
                        print(f"  {subject_code}: {present}/{total_classes} ({percentage}%)")
                
                except (ValueError, IndexError) as e:
                    if debug:
                        print(f"⚠️ Error parsing {subject_code}: {e}")
                    continue
    
    if debug:
        print(f"\n✅ Extracted {len(attendance_data)} subject records")
    
    return attendance_data