// src/components/LoginForm.js

import React, { useState } from "react";
import { fetchCaptcha, fetchAttendance } from "../services/api";

function LoginForm({ onLoginSuccess }) {
  // STATE - Data that can change
  // Think of state as variables that trigger re-render when changed

  const [rollNo, setRollNo] = useState(""); // Student roll number
  const [password, setPassword] = useState(""); // Student password
  const [captchaText, setCaptchaText] = useState(""); // User's CAPTCHA input
  const [captchaImage, setCaptchaImage] = useState(null); // CAPTCHA image from backend
  const [loading, setLoading] = useState(false); // Is something loading?
  const [error, setError] = useState(""); // Error message to show

  // FUNCTION 1: Get CAPTCHA when user clicks button
  const handleGetCaptcha = async () => {
    // Validate roll number first
    if (!rollNo) {
      setError("Please enter your roll number first");
      return;
    }

    setLoading(true); // Show loading state
    setError(""); // Clear any previous errors

    try {
      // Call our API service
      const response = await fetchCaptcha(rollNo);

      if (response.success) {
        // Store the CAPTCHA image in state
        setCaptchaImage(response.captcha_base64);
        setError("");
      } else {
        setError(response.error || "Failed to fetch CAPTCHA");
      }
    } catch (err) {
      setError("Network error. Is the backend running?");
    } finally {
      setLoading(false); // Stop loading
    }
  };

  // FUNCTION 2: Submit the form
  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent page reload on form submit

    // Validate all fields
    if (!rollNo || !password || !captchaText) {
      setError("Please fill all fields");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Call API to get attendance
      const response = await fetchAttendance({
        rollNo,
        password,
        captcha: captchaText,
        year: 0,
        semester: 0,
      });

      if (response.success) {
        // Pass data to parent component (App.js)
        onLoginSuccess(response.data);
      } else {
        setError(response.error || "Failed to fetch attendance");
      }
    } catch (err) {
      setError("Network error. Check backend and try again.");
    } finally {
      setLoading(false);
    }
  };

  // RENDER - What the user sees
  return (
    <div style={styles.container}>
      <h1>🎓 Attendance Dashboard</h1>

      {/* Error message */}
      {error && <div style={styles.error}>⚠️ {error}</div>}

      <form onSubmit={handleSubmit} style={styles.form}>
        {/* Roll Number Input */}
        <div style={styles.inputGroup}>
          <label>Roll Number:</label>
          <input
            type="text"
            value={rollNo}
            onChange={(e) => setRollNo(e.target.value)}
            placeholder="Enter your roll number"
            style={styles.input}
          />
        </div>

        {/* Password Input */}
        <div style={styles.inputGroup}>
          <label>Password:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            style={styles.input}
          />
        </div>

        {/* Get CAPTCHA Button */}
        <button
          type="button"
          onClick={handleGetCaptcha}
          disabled={loading}
          style={styles.captchaButton}
        >
          {loading ? "Loading..." : "🔄 Get CAPTCHA"}
        </button>

        {/* Display CAPTCHA Image */}
        {captchaImage && (
          <div style={styles.captchaContainer}>
            <img src={captchaImage} alt="CAPTCHA" style={styles.captchaImage} />
          </div>
        )}

        {/* CAPTCHA Input */}
        {captchaImage && (
          <div style={styles.inputGroup}>
            <label>Enter CAPTCHA:</label>
            <input
              type="text"
              value={captchaText}
              onChange={(e) => setCaptchaText(e.target.value)}
              placeholder="Type the text above"
              style={styles.input}
            />
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !captchaImage}
          style={styles.submitButton}
        >
          {loading ? "Loading..." : "📊 Get Attendance"}
        </button>
      </form>
    </div>
  );
}

// STYLES - Inline CSS for this component
const styles = {
  container: {
    maxWidth: "500px",
    margin: "50px auto",
    padding: "20px",
    border: "1px solid #ddd",
    borderRadius: "8px",
    backgroundColor: "#f9f9f9",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "15px",
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
  },
  input: {
    padding: "10px",
    fontSize: "16px",
    border: "1px solid #ccc",
    borderRadius: "4px",
  },
  captchaButton: {
    padding: "10px",
    fontSize: "16px",
    backgroundColor: "#007bff",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
  },
  captchaContainer: {
    textAlign: "center",
    padding: "10px",
    backgroundColor: "white",
    border: "1px solid #ddd",
    borderRadius: "4px",
  },
  captchaImage: {
    maxWidth: "100%",
  },
  submitButton: {
    padding: "12px",
    fontSize: "18px",
    backgroundColor: "#28a745",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
  },
  error: {
    padding: "10px",
    backgroundColor: "#f8d7da",
    color: "#721c24",
    borderRadius: "4px",
    marginBottom: "15px",
  },
};

export default LoginForm;
