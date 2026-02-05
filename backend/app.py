from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import time
import uuid
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading

app = Flask(__name__)
CORS(app)

# Store active browser sessions
active_sessions = {}

# Session timeout (5 minutes)
SESSION_TIMEOUT = timedelta(minutes=5)


def cleanup_expired_sessions():
    """Background task to cleanup expired sessions"""
    while True:
        try:
            time.sleep(60)
            now = datetime.now()
            expired = []
            
            for session_id, session in list(active_sessions.items()):
                if now - session['created_at'] > SESSION_TIMEOUT:
                    expired.append(session_id)
            
            for session_id in expired:
                try:
                    active_sessions[session_id]['driver'].quit()
                    del active_sessions[session_id]
                    print(f"🧹 Cleaned up expired session: {session_id}")
                except Exception as e:
                    print(f"⚠️  Error cleaning session {session_id}: {e}")
                    
        except Exception as e:
            print(f"⚠️  Error in cleanup thread: {e}")


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
cleanup_thread.start()


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "Attendance Dashboard API",
        "version": "2.1",
        "endpoints": {
            "GET /api/health": "Health check",
            "POST /api/captcha": "Get CAPTCHA image",
            "POST /api/attendance": "Get attendance with CAPTCHA"
        }
    })


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "active_sessions": len(active_sessions)
    }), 200


@app.route('/api/captcha', methods=['POST'])
def get_captcha():
    """
    Fetch CAPTCHA image and keep browser session alive
    CRITICAL: Keeps driver in login frame for next step
    """
    driver = None
    try:
        data = request.get_json()
        roll_no = data.get('roll_no')
        
        if not roll_no:
            return jsonify({
                "success": False,
                "error": "roll_no is required"
            }), 400
        
        print(f"\n{'='*60}")
        print(f"📸 NEW CAPTCHA REQUEST")
        print(f"{'='*60}")
        print(f"👤 Roll Number: {roll_no[:3]}***")
        
        # Setup browser
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        
        wait = WebDriverWait(driver, 15)
        
        # Navigate to login page
        print("🌐 Opening IMS portal...")
        driver.get("https://www.imsnsit.org/imsnsit/")
        print(f"✅ Loaded: {driver.current_url}")
        
        # Click Student Login
        print("🔗 Clicking Student Login link...")
        login_link = wait.until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Student Login"))
        )
        login_link.click()
        time.sleep(3)
        
        # Switch to login frame
        print("🔄 Switching to login frame...")
        wait.until(EC.frame_to_be_available_and_switch_to_it(0))
        print("✅ In login frame")
        
        # Fill roll number
        print("📝 Filling roll number...")
        uid_input = wait.until(EC.presence_of_element_located((By.ID, "uid")))
        uid_input.clear()
        uid_input.send_keys(roll_no)
        
        # Verify roll number was entered
        entered_value = uid_input.get_attribute('value')
        if entered_value == roll_no:
            print(f"✅ Roll number verified: {roll_no[:3]}***")
        else:
            print(f"⚠️  Roll number mismatch! Expected: {roll_no[:3]}***, Got: {entered_value[:3]}***")
        
        # Wait for CAPTCHA image to load
        print("⏳ Waiting for CAPTCHA image...")
        captcha_img = wait.until(EC.presence_of_element_located((By.ID, "captchaimg")))
        time.sleep(1)  # Give it a moment to fully render
        
        # Verify CAPTCHA element
        print(f"✅ CAPTCHA element found")
        print(f"   - Tag: {captcha_img.tag_name}")
        print(f"   - Size: {captcha_img.size}")
        
        # CRITICAL: Screenshot the CAPTCHA element directly
        print("📸 Taking CAPTCHA screenshot...")
        captcha_screenshot = captcha_img.screenshot_as_base64
        
        # Verify screenshot
        if captcha_screenshot and len(captcha_screenshot) > 100:
            print(f"✅ CAPTCHA screenshot captured ({len(captcha_screenshot)} bytes)")
        else:
            print(f"⚠️  CAPTCHA screenshot seems too small ({len(captcha_screenshot)} bytes)")
        
        # Verify we can still see all fields (debug)
        try:
            pwd_check = driver.find_element(By.ID, "pwd")
            captcha_check = driver.find_element(By.ID, "captcha")
            submit_check = driver.find_element(By.NAME, "submit")
            print("✅ Verified all form fields are accessible")
        except Exception as e:
            print(f"⚠️  Warning: Could not verify all form fields: {e}")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # CRITICAL: Store driver WITHOUT switching out of frame
        # The next request will continue from here
        active_sessions[session_id] = {
            'driver': driver,
            'roll_no': roll_no,
            'created_at': datetime.now(),
            'in_frame': True  # Flag to indicate driver is in login frame
        }
        
        print(f"\n{'='*60}")
        print(f"✅ SESSION CREATED")
        print(f"{'='*60}")
        print(f"🆔 Session ID: {session_id[:8]}...")
        print(f"👤 Roll Number: {roll_no[:3]}***")
        print(f"📊 Active sessions: {len(active_sessions)}")
        print(f"⏰ Expires at: {(datetime.now() + SESSION_TIMEOUT).strftime('%H:%M:%S')}")
        print(f"🔒 Frame locked: YES (in frame 0)")
        print(f"{'='*60}\n")
        
        return jsonify({
            "success": True,
            "captcha_base64": f"data:image/png;base64,{captcha_screenshot}",
            "session_id": session_id,
            "roll_no": roll_no
        }), 200
            
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ CAPTCHA FETCH FAILED")
        print(f"{'='*60}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        # Clean up driver on error
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/attendance', methods=['POST'])
def get_attendance():
    """
    Get attendance using existing session
    Driver is already in login frame with roll number filled
    """
    session_id = None
    
    try:
        data = request.get_json()
        
        session_id = data.get('session_id')
        password = data.get('password')
        captcha = data.get('captcha')
        year_idx = data.get('year', 0)
        sem_idx = data.get('semester', 0)
        
        # Validate
        if not all([session_id, password, captcha]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: session_id, password, captcha"
            }), 400
        
        # Get the existing browser session
        session = active_sessions.get(session_id)
        
        if not session:
            return jsonify({
                "success": False,
                "error": "Session expired or invalid. Please get CAPTCHA again."
            }), 400
        
        driver = session['driver']
        roll_no = session['roll_no']
        
        print(f"\n{'='*60}")
        print(f"📊 ATTENDANCE REQUEST")
        print(f"{'='*60}")
        print(f"🆔 Session: {session_id[:8]}...")
        print(f"👤 Roll: {roll_no[:3]}***")
        print(f"🔐 Password: {'*' * len(password)} ({len(password)} chars)")
        print(f"🔤 CAPTCHA: {captcha}")
        print(f"📅 Year index: {year_idx}")
        print(f"📅 Semester index: {sem_idx}")
        print(f"⏱️  Session age: {(datetime.now() - session['created_at']).seconds}s")
        print(f"{'='*60}\n")
        
        # Import scraper function
        from scraper.scraper_with_driver import scrape_attendance_with_driver
        
        # Use the EXISTING driver
        # Driver is already in login frame with roll number filled
        result = scrape_attendance_with_driver(
            driver=driver,
            password=password,
            captcha=captcha,
            year_idx=year_idx,
            semester_idx=sem_idx
        )
        
        # Clean up - remove session and quit browser
        try:
            del active_sessions[session_id]
            driver.quit()
            print(f"\n{'='*60}")
            print(f"✅ SESSION CLEANUP")
            print(f"{'='*60}")
            print(f"🆔 Cleaned up: {session_id[:8]}...")
            print(f"📊 Remaining sessions: {len(active_sessions)}")
            print(f"{'='*60}\n")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ ATTENDANCE FETCH FAILED")
        print(f"{'='*60}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        # Clean up on error
        if session_id and session_id in active_sessions:
            try:
                active_sessions[session_id]['driver'].quit()
                del active_sessions[session_id]
                print(f"🧹 Cleaned up session after error: {session_id[:8]}...")
            except Exception as cleanup_error:
                print(f"⚠️  Error during error cleanup: {cleanup_error}")
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/debug/sessions', methods=['GET'])
def debug_sessions():
    """Debug endpoint to check active sessions"""
    return jsonify({
        'active_sessions': len(active_sessions),
        'sessions': [
            {
                'session_id': sid[:8] + '...',
                'roll_no': sess['roll_no'][:3] + '***',
                'age_seconds': (datetime.now() - sess['created_at']).seconds,
                'in_frame': sess.get('in_frame', False)
            }
            for sid, sess in active_sessions.items()
        ]
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎯 ATTENDANCE DASHBOARD API v2.1")
    print("="*60)
    print("🌐 Server: http://localhost:5001")
    print(f"⏰ Session timeout: {SESSION_TIMEOUT.seconds // 60} minutes")
    print("\n📋 Endpoints:")
    print("  GET  /                      - API info")
    print("  GET  /api/health            - Health check")
    print("  POST /api/captcha           - Get CAPTCHA (creates session)")
    print("  POST /api/attendance        - Get attendance (uses session)")
    print("  GET  /api/debug/sessions    - View active sessions")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5001, host='0.0.0.0')