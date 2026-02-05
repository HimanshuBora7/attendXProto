"""
Scraper that continues with existing driver session
Enhanced version with robust frame handling
"""
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from .utils import find_and_expand_tree_node, find_and_click_link, extract_attendance_table_enhanced


def scrape_attendance_with_driver(driver, password, captcha, year_idx=0, semester_idx=0):
    """
    Continue scraping with existing driver session
    
    IMPORTANT: Driver should already be on login page with roll number filled
    
    Args:
        driver: Existing Selenium WebDriver instance
        password (str): Student password
        captcha (str): CAPTCHA text to submit
        year_idx (int): Year dropdown index (default 0)
        semester_idx (int): Semester dropdown index (default 0)
    
    Returns:
        dict: {
            'success': bool,
            'data': list of attendance records,
            'error': str (if failed)
        }
    """
    try:
        print("🔐 Continuing login with existing session...")
        print(f"📍 Current URL: {driver.current_url}")
        
        wait = WebDriverWait(driver, 15)
        
        # CRITICAL: Ensure we're in the login frame
        # The driver might have switched out, so let's ensure we're in the right place
        try:
            print("🔄 Ensuring we're in the login frame...")
            driver.switch_to.default_content()
            
            # Wait for frame to be available and switch to it
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))
            print("✅ Switched to login frame (frame 0)")
            
            # Verify we can see the login form
            uid_field = driver.find_element(By.ID, "uid")
            print(f"✅ Found UID field with value: {uid_field.get_attribute('value')[:3]}***")
            
        except Exception as e:
            print(f"⚠️ Frame switching issue: {e}")
            return {
                'success': False,
                'error': f'Could not access login frame: {str(e)}'
            }
        
        # STEP 1: Fill password
        try:
            print("📝 Filling password...")
            
            # Wait for password field to be present
            pwd_input = wait.until(EC.presence_of_element_located((By.ID, "pwd")))
            pwd_input.clear()
            time.sleep(0.5)
            pwd_input.send_keys(password)
            
            # Verify password was entered
            if pwd_input.get_attribute('value'):
                print("✅ Password entered successfully")
            else:
                print("⚠️ Password field appears empty after entry")
                
        except TimeoutException:
            return {
                'success': False,
                'error': 'Timeout: Could not find password field. Page may not have loaded.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Could not fill password field: {str(e)}'
            }
        
        # STEP 2: Fill CAPTCHA
        try:
            print(f"🔤 Filling CAPTCHA: {captcha}")
            
            # Wait for CAPTCHA field to be present
            captcha_input = wait.until(EC.presence_of_element_located((By.ID, "captcha")))
            captcha_input.clear()
            time.sleep(0.5)
            captcha_input.send_keys(captcha)
            
            # Verify CAPTCHA was entered
            if captcha_input.get_attribute('value') == captcha:
                print("✅ CAPTCHA entered and verified")
            else:
                print(f"⚠️ CAPTCHA mismatch. Expected: {captcha}, Got: {captcha_input.get_attribute('value')}")
                
        except TimeoutException:
            # Debug: Print page source to see what's there
            print("🔍 DEBUG: Login frame HTML:")
            print(driver.page_source[:500])
            
            return {
                'success': False,
                'error': 'Timeout: Could not find CAPTCHA field. The login page structure may have changed.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Could not fill CAPTCHA field: {str(e)}'
            }
        
        # STEP 3: Submit login form
        try:
            print("🚀 Submitting login form...")
            submit_btn = wait.until(EC.element_to_be_clickable((By.NAME, "submit")))
            
            # Take screenshot before submit (for debugging)
            try:
                driver.save_screenshot("/tmp/before_submit.png")
                print("📸 Saved screenshot: /tmp/before_submit.png")
            except:
                pass
            
            submit_btn.click()
            print("✅ Clicked submit button")
            time.sleep(5)  # Wait for login to process
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Could not click submit button: {str(e)}'
            }
        
        # STEP 4: Verify login success
        print("🔍 Verifying login...")
        driver.switch_to.default_content()
        
        # Wait a bit for page to load
        time.sleep(2)
        
        page_source = driver.page_source.lower()
        print(f"📄 Page source length: {len(page_source)} characters")
        
        if "logout" not in page_source:
            # Take screenshot of failed login
            try:
                driver.save_screenshot("/tmp/login_failed.png")
                print("📸 Saved screenshot: /tmp/login_failed.png")
            except:
                pass
            
            # Try to find specific error message
            error_msg = "Login failed - Invalid credentials or CAPTCHA"
            
            if "invalid" in page_source or "wrong" in page_source:
                error_msg = "Invalid credentials or CAPTCHA"
            elif "captcha" in page_source:
                error_msg = "Incorrect CAPTCHA - Please try again"
            elif "password" in page_source and "incorrect" in page_source:
                error_msg = "Incorrect password"
            
            print(f"❌ Login failed: {error_msg}")
            print(f"🔍 Page title: {driver.title}")
            
            return {
                'success': False,
                'error': error_msg
            }
        
        print("✅ Login successful!")
        
        # STEP 5: Navigate to Attendance section
        print("📚 Navigating to Attendance...")
        
        if not find_and_click_link(driver, ['Academics']):
            return {
                'success': False,
                'error': 'Could not find Academics link'
            }
        time.sleep(3)
        
        # Expand Attendance tree node
        print("🌳 Expanding Attendance tree node...")
        find_and_expand_tree_node(driver, ['Attendance'])
        time.sleep(2)
        
        # Click My Attendance
        print("🎯 Clicking My Attendance...")
        if not find_and_click_link(driver, ['My Attendance'], exact_match=True):
            return {
                'success': False,
                'error': 'Could not find My Attendance link'
            }
        
        time.sleep(5)
        
        # STEP 6: Select Year and Semester
        print("📅 Selecting Year and Semester...")
        
        year_selected = False
        semester_selected = False
        submit_clicked = False
        
        for frame_name in ['data', 'contents', 'bottom', 'top']:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame_name)
                
                selects = driver.find_elements(By.TAG_NAME, "select")
                
                for select_elem in selects:
                    try:
                        select = Select(select_elem)
                        select_name = (select_elem.get_attribute("name") or 
                                     select_elem.get_attribute("id") or "").lower()
                        
                        # Select Year
                        if not year_selected and any(keyword in select_name for keyword in ['year', 'yr']):
                            if year_idx < len(select.options):
                                select.select_by_index(year_idx)
                                print(f"✅ Selected Year: {select.options[year_idx].text}")
                                year_selected = True
                                time.sleep(1)
                            else:
                                print(f"⚠️  Year index {year_idx} out of range (max: {len(select.options)-1})")
                        
                        # Select Semester
                        elif not semester_selected and any(keyword in select_name for keyword in ['sem', 'semester']):
                            if semester_idx < len(select.options):
                                select.select_by_index(semester_idx)
                                print(f"✅ Selected Semester: {select.options[semester_idx].text}")
                                semester_selected = True
                                time.sleep(1)
                            else:
                                print(f"⚠️  Semester index {semester_idx} out of range (max: {len(select.options)-1})")
                                
                    except Exception as e:
                        print(f"⚠️  Error selecting dropdown: {e}")
                        continue
                
                # If both selected, find and click submit
                if year_selected and semester_selected:
                    buttons = driver.find_elements(By.TAG_NAME, "input") + \
                             driver.find_elements(By.TAG_NAME, "button")
                    
                    for button in buttons:
                        try:
                            button_type = (button.get_attribute("type") or "").lower()
                            button_value = (button.get_attribute("value") or button.text or "").lower()
                            button_name = (button.get_attribute("name") or "").lower()
                            
                            # Skip PDF/download buttons
                            if any(skip in button_value for skip in ['pdf', 'download', 'export']):
                                continue
                            if 'mpdfx' in button_name:
                                continue
                            
                            # Click submit button
                            if (button_type == "submit" and button_name == "submit") or \
                               button_value == "submit":
                                print(f"✅ Clicking Submit button...")
                                button.click()
                                submit_clicked = True
                                time.sleep(5)
                                break
                        except Exception as e:
                            print(f"⚠️  Error clicking button: {e}")
                            continue
                    
                    if submit_clicked:
                        break
                    
            except Exception as e:
                print(f"⚠️  Error in frame '{frame_name}': {e}")
                continue
        
        if not year_selected or not semester_selected:
            return {
                'success': False,
                'error': 'Could not find Year/Semester dropdowns'
            }
        
        if not submit_clicked:
            print("⚠️  Warning: Submit button may not have been clicked")
        
        # STEP 7: Extract attendance data
        print("📊 Extracting attendance data...")
        
        all_attendance = []
        frames_checked = []
        
        for frame_name in ['data', 'contents', 'bottom', 'top']:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame_name)
                
                html = driver.page_source
                frames_checked.append(frame_name)
                
                # Check if frame contains attendance data
                if 'attend' in html.lower() and len(html) > 500:
                    print(f"✅ Found attendance data in '{frame_name}' frame")
                    
                    # Optional: Save HTML for debugging
                    try:
                        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
                        os.makedirs(data_dir, exist_ok=True)
                        
                        html_file = os.path.join(data_dir, f"attendance_{frame_name}.html")
                        with open(html_file, "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"💾 Saved HTML to {html_file}")
                    except Exception as e:
                        print(f"⚠️  Could not save HTML: {e}")
                    
                    # Parse attendance table
                    attendance_rows = extract_attendance_table_enhanced(html, debug=False)
                    
                    if attendance_rows:
                        all_attendance.extend(attendance_rows)
                        print(f"✅ Extracted {len(attendance_rows)} subjects from '{frame_name}'")
                    else:
                        print(f"⚠️  No attendance rows extracted from '{frame_name}'")
                    
            except Exception as e:
                print(f"⚠️  Error processing frame '{frame_name}': {e}")
                continue
        
        # Switch back to default content
        driver.switch_to.default_content()
        
        if not all_attendance:
            return {
                'success': False,
                'error': f'No attendance data found. Checked frames: {frames_checked}'
            }
        
        print(f"🎉 Successfully extracted {len(all_attendance)} subjects!")
        
        return {
            'success': True,
            'data': all_attendance,
            'total_subjects': len(all_attendance)
        }
        
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to save debug screenshot
        try:
            driver.save_screenshot("/tmp/error_screenshot.png")
            print("📸 Saved error screenshot: /tmp/error_screenshot.png")
        except:
            pass
        
        return {
            'success': False,
            'error': f'Scraping error: {str(e)}'
        }