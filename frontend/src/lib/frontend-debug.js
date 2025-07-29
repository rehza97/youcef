// Frontend debug utility for browser console testing
class FrontendDebugger {
  constructor() {
    this.api = null;
    this.auth = null;
    this.websocket = null;
  }

  // Initialize debugger with app instances
  init(api, auth, websocket) {
    this.api = api;
    this.auth = auth;
    this.websocket = websocket;
    console.log("🔍 Frontend debugger initialized");
  }

  // Test authentication
  async testAuth() {
    console.log("🔐 Testing authentication...");
    try {
      const response = await fetch("http://127.0.0.1:8000/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: "admin",
          password: "admin123",
        }),
      });

      const data = await response.json();
      console.log("📊 Auth response:", data);
      return data;
    } catch (error) {
      console.error("❌ Auth test failed:", error);
      return null;
    }
  }

  // Test file upload
  async testFileUpload(token) {
    console.log("📁 Testing file upload...");
    try {
      // Create test file
      const testContent = "name,age,city\nJohn,25,Paris\nJane,30,London";
      const blob = new Blob([testContent], { type: "text/csv" });
      const file = new File([blob], "test_debug.csv", { type: "text/csv" });

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://127.0.0.1:8000/api/files/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      console.log("📊 Upload response:", data);
      return data;
    } catch (error) {
      console.error("❌ File upload test failed:", error);
      return null;
    }
  }

  // Test WebSocket connection
  testWebSocket(token, userId = 1) {
    console.log("🔌 Testing WebSocket connection...");
    try {
      const ws = new WebSocket(
        `ws://localhost:8000/ws/notifications/${userId}/?token=${token}`
      );

      ws.onopen = () => {
        console.log("✅ WebSocket connected");
        ws.send(JSON.stringify({ type: "ping" }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("📥 WebSocket message:", data);
      };

      ws.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
      };

      ws.onclose = (event) => {
        console.log("🔌 WebSocket closed:", event.code, event.reason);
      };

      return ws;
    } catch (error) {
      console.error("❌ WebSocket test failed:", error);
      return null;
    }
  }

  // Test API endpoints
  async testAPIEndpoints(token) {
    console.log("🌐 Testing API endpoints...");
    const endpoints = [
      "/api/users/",
      "/api/files/",
      "/api/notifications/",
      "/api/health/detailed",
    ];

    for (const endpoint of endpoints) {
      try {
        const response = await fetch(`http://127.0.0.1:8000${endpoint}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await response.json();
        console.log(`📊 ${endpoint}:`, { status: response.status, data });
      } catch (error) {
        console.error(`❌ ${endpoint} failed:`, error);
      }
    }
  }

  // Run comprehensive test
  async runFullTest() {
    console.log("🚀 Starting comprehensive frontend test...");

    // Test 1: Authentication
    const authResult = await this.testAuth();
    if (!authResult || !authResult.access_token) {
      console.error("❌ Authentication failed");
      return;
    }

    const token = authResult.access_token;
    console.log("✅ Authentication successful");

    // Test 2: API endpoints
    await this.testAPIEndpoints(token);

    // Test 3: File upload
    await this.testFileUpload(token);

    // Test 4: WebSocket
    this.testWebSocket(token);

    console.log("✅ All frontend tests completed!");
  }

  // Debug current app state
  debugAppState() {
    console.log("🔍 Current app state:");
    console.log("- Auth context:", this.auth);
    console.log("- API instance:", this.api);
    console.log("- WebSocket:", this.websocket);

    // Check localStorage
    console.log("- LocalStorage:", {
      token: localStorage.getItem("token"),
      user: localStorage.getItem("user"),
      rememberMe: localStorage.getItem("rememberMe"),
    });

    // Check sessionStorage
    console.log("- SessionStorage:", {
      token: sessionStorage.getItem("token"),
      user: sessionStorage.getItem("user"),
    });
  }
}

// Create global debug instance
window.frontendDebug = new FrontendDebugger();

// Export for use in components
export const frontendDebug = window.frontendDebug;

// Auto-initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  console.log(
    "🔍 Frontend debugger ready! Use window.frontendDebug.runFullTest() to test"
  );
});
