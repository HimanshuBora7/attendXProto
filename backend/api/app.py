"""
Flask API for Attendance Dashboard
Provides endpoints for CAPTCHA fetching and attendance scraping
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
CORS(app)


@app.route('/', methods=['GET'])
def home():
    """API information endpoint"""
    return jsonify({
        "name": "Attendance Dashboard API",
        "version": "2.0",
        "endpoints": {
            "GET /api/health": "Health check",
            "POST /api/captcha": "Get CAPTCHA image",
            "POST /api/attendance": "Get attendance with CAPTCHA"
        }
    })


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


@app.route('/api/captcha', methods=['POST'])
def get_captcha():
    """
    Fetch CAPTCHA image from IMS portal
    
    Request:
    {
        "roll_no": "202300123"
    }
    
    Response:
    {
        "success": true,
        "captcha_url": "https://www.imsnsit.org/imsnsit/images/captcha/captcha_1770243588.jpg",
        "captcha_base64": "data:image/jpeg;base64,..."
    }
    """
    try:
        data = request.get_json()
        roll_no = data.get('roll_no')
        
        if not roll_no:
            return jsonify({
                "success": False,
                "error": "roll_no is required"
            }), 400
        
        print(f"📸 Fetching CAPTCHA for: {roll_no[:3]}***")
        
        # Setup browser
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Keep visible for debugging
        # options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        
        try:
            # Navigate to login page
            driver.get("https://www.imsnsit.org/imsnsit/")
            
            wait = WebDriverWait(driver, 10)
            login_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Student Login")))
            login_link.click()
            time.sleep(3)
            
            # Switch to login frame
            driver.switch_to.frame(0)
            
            # Fill roll number
            uid_input = wait.until(EC.presence_of_element_located((By.ID, "uid")))
            uid_input.send_keys(roll_no)
            
            # Get CAPTCHA image URL
            captcha_img = driver.find_element(By.ID, "captchaimg")
            captcha_src = captcha_img.get_attribute("src")
            
            # Make absolute URL
            if captcha_src.startswith("images/"):
                captcha_url = f"https://www.imsnsit.org/imsnsit/{captcha_src}"
            else:
                captcha_url = captcha_src
            
            print(f"📸 CAPTCHA URL: {captcha_url}")
            
            # Fetch image using session with cookies
            cookies = driver.get_cookies()
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            img_response = session.get(captcha_url)
            img_base64 = base64.b64encode(img_response.content).decode('utf-8')
            
            driver.quit()
            
            return jsonify({
                "success": True,
                "captcha_url": captcha_url,
                "captcha_base64": f"data:image/jpeg;base64,{img_base64}",
                "roll_no": roll_no
            }), 200
            
        except Exception as e:
            driver.quit()
            raise e
            
    except Exception as e:
        print(f"❌ Error fetching CAPTCHA: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/attendance', methods=['POST'])
def get_attendance():
    """
    Get attendance data
    
    Request:
    {
        "roll_no": "202300123",
        "password": "password",
        "captcha": "abc123",
        "year": 0,
        "semester": 0
    }
    
    Response:
    {
        "success": true,
        "data": [...attendance records...],
        "total_subjects": 6
    }
    """
    try:
        # Import here to avoid circular imports
        from scraper.scraper import scrape_attendance
        
        data = request.get_json()
        
        roll_no = data.get('roll_no')
        password = data.get('password')
        captcha = data.get('captcha')
        year_idx = data.get('year', 0)
        sem_idx = data.get('semester', 0)
        
        # Validate required fields
        if not all([roll_no, password, captcha]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: roll_no, password, captcha"
            }), 400
        
        print(f"📊 Scraping attendance for: {roll_no[:3]}***")
        
        # CAPTCHA solver function
        def captcha_solver(driver):
            return captcha
        
        # Call scraper
        result = scrape_attendance(
            roll_no=roll_no,
            password=password,
            year_idx=year_idx,
            semester_idx=sem_idx,
            captcha_solver=captcha_solver,
            headless=False  # Keep visible for debugging
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎓 ATTENDANCE DASHBOARD API v2.0")
    print("="*60)
    print("🌐 Server: http://localhost:5000")
    print("\n📋 Endpoints:")
    print("  GET  /                    - API info")
    print("  GET  /api/health          - Health check")
    print("  POST /api/captcha         - Get CAPTCHA image")
    print("  POST /api/attendance      - Get attendance data")
    print("\n💡 Workflow:")
    print("  1. Frontend calls /api/captcha with roll_no")
    print("  2. API returns CAPTCHA image (base64)")
    print("  3. User solves CAPTCHA")
    print("  4. Frontend calls /api/attendance with all data")
    print("  5. API returns attendance data")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5001, host='0.0.0.0')