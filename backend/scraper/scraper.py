"""
Main attendance scraper function
Logs into IMS portal and extracts attendance data
"""
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from .utils import find_and_expand_tree_node, find_and_click_link, extract_attendance_table_enhanced


def scrape_attendance(roll_no, password, year_idx=0, semester_idx=0, captcha_solver=None, headless=True):
    """
    Scrape attendance data from IMS portal
    
    Args:
        roll_no (str): Student roll number
        password (str): Student password
        year_idx (int): Year dropdown index (default 0)
        semester_idx (int): Semester dropdown index (default 0)
        captcha_solver (callable): Function that returns CAPTCHA text when called with driver
        headless (bool): Run browser in headless mode
        
    Returns:
        dict: {
            'success': bool,
            'data': list of attendance records,
            'error': str (if failed)
        }
    """
    driver = None
    
    try:
        print(f"👤 Scraping for: {roll_no[:3]}***")
        
        # Setup browser
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if headless:
            options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        wait = WebDriverWait(driver, 10)
        
        # Step 1: Navigate to login page
        print("🌐 Opening IMS portal...")
        driver.get("https://www.imsnsit.org/imsnsit/")
        
        login_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Student Login")))
        login_link.click()
        time.sleep(3)
        
        # Step 2: Switch to login frame and fill credentials
        print("🔐 Logging in...")
        driver.switch_to.frame(0)
        
        uid_input = wait.until(EC.presence_of_element_located((By.ID, "uid")))
        uid_input.send_keys(roll_no)
        
        pwd_input = driver.find_element(By.ID, "pwd")
        pwd_input.send_keys(password)
        
        # Step 3: Handle CAPTCHA
        if captcha_solver:
            print("🔤 Solving CAPTCHA...")
            captcha_text = captcha_solver(driver)
            captcha_input = driver.find_element(By.ID, "captcha")
            captcha_input.send_keys(captcha_text)
        else:
            print("⚠️  No CAPTCHA solver provided, attempting without CAPTCHA")
        
        # Submit login
        submit_btn = driver.find_element(By.NAME, "submit")
        submit_btn.click()
        time.sleep(5)
        
        # Check if login successful
        driver.switch_to.default_content()
        if "logout" not in driver.page_source.lower():
            return {
                'success': False,
                'error': 'Login failed - Invalid credentials or CAPTCHA'
            }
        
        print("✅ Login successful!")
        
        # Step 4: Navigate to Attendance
        print("📚 Navigating to Attendance...")
        
        if not find_and_click_link(driver, ['Academics']):
            return {
                'success': False,
                'error': 'Could not find Academics link'
            }
        time.sleep(3)
        
        # Expand Attendance tree node
        if not find_and_expand_tree_node(driver, ['Attendance']):
            print("⚠️  Could not expand Attendance node automatically")
        
        time.sleep(2)
        
        # Click My Attendance
        if not find_and_click_link(driver, ['My Attendance'], exact_match=True):
            return {
                'success': False,
                'error': 'Could not find My Attendance link'
            }
        
        time.sleep(5)
        
        # Step 5: Select Year and Semester
        print("📅 Selecting Year and Semester...")
        
        year_selected = False
        semester_selected = False
        
        for frame_name in ['data', 'contents', 'bottom', 'top']:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame_name)
                
                selects = driver.find_elements(By.TAG_NAME, "select")
                
                for select_elem in selects:
                    select = Select(select_elem)
                    select_name = select_elem.get_attribute("name") or select_elem.get_attribute("id") or ""
                    
                    if not year_selected and any(keyword in select_name.lower() for keyword in ['year', 'yr']):
                        select.select_by_index(year_idx)
                        print(f"✅ Selected Year: {select.options[year_idx].text}")
                        year_selected = True
                        time.sleep(1)
                    
                    elif not semester_selected and any(keyword in select_name.lower() for keyword in ['sem', 'semester']):
                        select.select_by_index(semester_idx)
                        print(f"✅ Selected Semester: {select.options[semester_idx].text}")
                        semester_selected = True
                        time.sleep(1)
                
                if year_selected and semester_selected:
                    # Find and click submit button
                    buttons = driver.find_elements(By.TAG_NAME, "input") + driver.find_elements(By.TAG_NAME, "button")
                    
                    for button in buttons:
                        button_type = button.get_attribute("type") or ""
                        button_value = (button.get_attribute("value") or button.text or "").lower()
                        button_name = (button.get_attribute("name") or "").lower()
                        
                        # Skip PDF/download buttons
                        if 'pdf' in button_value or 'download' in button_value or 'mpdfx' in button_name:
                            continue
                        
                        if (button_type.lower() == "submit" and button_name == "submit") or button_value == "submit":
                            print("✅ Clicking Submit...")
                            button.click()
                            time.sleep(5)
                            break
                    
                    break
                    
            except Exception as e:
                continue
        
        if not year_selected or not semester_selected:
            return {
                'success': False,
                'error': 'Could not find Year/Semester dropdowns'
            }
        
        # Step 6: Extract attendance data
        print("📊 Extracting attendance data...")
        
        all_attendance = []
        
        for frame_name in ['data', 'contents', 'bottom', 'top']:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame_name)
                
                html = driver.page_source
                
                if 'attend' in html.lower() and len(html) > 500:
                    print(f"✅ Found attendance data in '{frame_name}' frame")
                    
                    # Save HTML for debugging (optional)
                    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
                    os.makedirs(data_dir, exist_ok=True)
                    
                    html_file = os.path.join(data_dir, f"attendance_{frame_name}.html")
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    
                    # Parse attendance
                    attendance_rows = extract_attendance_table_enhanced(html, debug=False)
                    
                    if attendance_rows:
                        all_attendance.extend(attendance_rows)
                        print(f"✅ Extracted {len(attendance_rows)} subjects")
                    
            except Exception as e:
                print(f"⚠️  Error in frame '{frame_name}': {e}")
                continue
        
        if not all_attendance:
            return {
                'success': False,
                'error': 'No attendance data found'
            }
        
        print(f"🎉 Successfully extracted data for {len(all_attendance)} subjects!")
        
        return {
            'success': True,
            'data': all_attendance,
            'total_subjects': len(all_attendance)
        }
        
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }
        
    finally:
        if driver:
            driver.quit()