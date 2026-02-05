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
    Enhanced attendance table parser with better debugging
    Handles various IMS table formats
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
    subject_names = {}
    
    for table_idx, table in enumerate(tables):
        if debug:
            print(f"\n--- Analyzing Table {table_idx + 1} ---")
        
        rows = table.find_all('tr')
        if debug:
            print(f"   Rows: {len(rows)}")
        
        # Try to find header row with subject codes
        header_row = None
        header_row_idx = -1
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            if debug and row_idx < 5:
                print(f"   Row {row_idx}: {cell_texts[:10]}")
            
            # Look for subject codes
            has_subject_codes = any(
                bool(re.match(r'^[A-Z]{2,4}[A-Z]?\d{3,4}$', text)) 
                for text in cell_texts
            )
            
            if has_subject_codes or 'Days' in cell_texts:
                header_row = cell_texts
                header_row_idx = row_idx
                if debug:
                    print(f"\n   ✅ Found header row at index {row_idx}")
                    print(f"   Header: {header_row}")
                break
        
        if not header_row:
            if debug:
                print("   ⚠️  No header row found in this table")
            continue
        
        # Extract subject codes
        subject_codes = []
        for i, cell in enumerate(header_row):
            if i == 0:
                continue
            if re.match(r'^[A-Z]{2,4}[A-Z]?\d{3,4}$', cell):
                subject_codes.append(cell)
            elif cell and cell != 'Days':
                subject_codes.append(cell)
        
        if debug:
            print(f"   📚 Subject codes: {subject_codes}")
        
        # Look for subject names row
        if header_row_idx + 1 < len(rows):
            name_row = rows[header_row_idx + 1]
            name_cells = name_row.find_all(['td', 'th'])
            name_texts = [cell.get_text(strip=True) for cell in name_cells]
            
            for i, code in enumerate(subject_codes):
                if i + 1 < len(name_texts):
                    subject_names[code] = name_texts[i + 1]
            
            if debug:
                print(f"   📖 Subject names found: {len(subject_names)}")
        
        # Parse attendance rows (P/A format)
        for row_idx in range(header_row_idx + 2, len(rows)):
            row = rows[row_idx]
            cells = row.find_all(['td', 'th'])
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            if len(cell_texts) < 2:
                continue
            
            # Skip total rows
            if any(keyword in cell_texts[0].lower() for keyword in ['total', 'overall', 'grand']):
                for i, code in enumerate(subject_codes):
                    if i + 1 < len(cell_texts):
                        stats = cell_texts[i + 1]
                        
                        # Parse "P/A" or "P / A" format
                        match = re.search(r'(\d+)\s*/\s*(\d+)', stats)
                        if match:
                            present = int(match.group(1))
                            absent = int(match.group(2))
                            total = present + absent
                            percentage = round((present / total * 100), 2) if total > 0 else 0
                            
                            attendance_data.append({
                                'Subject Code': code,
                                'Subject Name': subject_names.get(code, 'N/A'),
                                'Classes Present': present,
                                'Classes Absent': absent,
                                'Total Classes': total,
                                'Attendance %': percentage
                            })
                break
    
    if debug:
        print(f"\n✅ Extracted {len(attendance_data)} subject records")
    
    return attendance_data