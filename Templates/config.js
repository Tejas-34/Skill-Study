const API_BASE_URL = window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"  // Development API URL
    : "https://api.yourdomain.com"; // Production API URL

export { API_BASE_URL };
