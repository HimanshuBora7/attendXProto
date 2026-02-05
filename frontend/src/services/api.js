// src/services/api.js

// Base URL of our Flask backend
const API_BASE_URL = "http://localhost:5001";

/**
 * API Service - Functions to communicate with backend
 */

// Function 1: Fetch CAPTCHA image
export const fetchCaptcha = async (rollNo) => {
  try {
    // Make a POST request to /api/captcha endpoint
    const response = await fetch(`${API_BASE_URL}/api/captcha`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json", // Tell server we're sending JSON
      },
      body: JSON.stringify({ roll_no: rollNo }), // Convert JS object to JSON string
    });

    // Convert response to JSON
    const data = await response.json();

    // Return the data
    return data;
  } catch (error) {
    console.error("Error fetching CAPTCHA:", error);
    throw error; // Pass error to component
  }
};

// Function 2: Fetch attendance data
export const fetchAttendance = async (credentials) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/attendance`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        roll_no: credentials.rollNo,
        password: credentials.password,
        captcha: credentials.captcha,
        year: credentials.year || 0,
        semester: credentials.semester || 0,
      }),
    });

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching attendance:", error);
    throw error;
  }
};
