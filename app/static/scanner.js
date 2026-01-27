let qrScanner;
let isScanning = true;

// Initialize QR Scanner
function initScanner() {
  const video = document.getElementById("qr-video");
  qrScanner = new QrScanner(video, onScanResult, {
    maxScansPerSecond: 5,
    highlightScanRegion: true,
    returnDetailedScanResult: true,
  });

  // Check for saved camera preference
  const savedCamera = localStorage.getItem("scannerCam");

  qrScanner
    .start()
    .then(() => {
      if (savedCamera && typeof savedCamera !== "undefined") {
        // Verify the saved camera still exists before trying to use it
        QrScanner.listCameras(true).then((cameras) => {
          const cameraExists = cameras.some((cam) => cam.id === savedCamera);
          if (cameraExists) {
            qrScanner.setCamera(savedCamera);
          }
        });
      }
    })
    .catch((err) => {
      console.error("Error starting scanner:", err);
      showError("Camera Error", "Unable to access camera");
    });
}

// Handle scan result
async function onScanResult(result) {
  if (!isScanning) return;

  console.log("Scanned:", result.data);
  qrScanner.stop();
  isScanning = false;

  try {
    // Call API to check dues status
    const response = await fetch(`/api/member/${result.data}/dues`);
    const data = await response.json();

    if (data.dues) {
      showSuccess();
    } else {
      showError();
    }
  } catch (error) {
    console.error("Error checking dues:", error);
    showError();
  }
}

// Show success (green)
function showSuccess() {
  const container = document.getElementById("scannerContainer");
  const statusMessage = document.getElementById("statusMessage");
  const clearInstruction = document.getElementById("clearInstruction");

  container.className = "scanner-container success";
  statusMessage.textContent = "Dues Paid ✓";
  statusMessage.classList.add("show");
  clearInstruction.classList.add("show");
}

// Show error (red)
function showError(title = "Dues Not Paid ✗", subtitle = "") {
  const container = document.getElementById("scannerContainer");
  const statusMessage = document.getElementById("statusMessage");
  const clearInstruction = document.getElementById("clearInstruction");

  container.className = "scanner-container error";
  statusMessage.textContent = title;
  statusMessage.classList.add("show");
  clearInstruction.classList.add("show");
}

// Clear and restart scanning
function clearAndRestart() {
  if (isScanning) return; // Already scanning

  const container = document.getElementById("scannerContainer");
  const statusMessage = document.getElementById("statusMessage");
  const clearInstruction = document.getElementById("clearInstruction");

  // Reset UI
  container.className = "scanner-container";
  statusMessage.classList.remove("show");
  clearInstruction.classList.remove("show");

  // Restart scanner
  setTimeout(() => {
    isScanning = true;
    qrScanner.start().catch((err) => {
      console.error("Error restarting scanner:", err);
    });
  }, 300);
}

// Switch camera functionality
async function switchCamera() {
  try {
    const cameras = await QrScanner.listCameras();

    if (cameras.length <= 1) {
      alert("Only one camera available");
      return;
    }

    // Get current camera ID. qrScanner doesn't expose a simple "getCurrentCameraId" method in all versions,
    // but usually we can infer it or we track it.
    // However, since we are setting it via localStorage, we can use that as a hint,
    // or try to find which one is active.
    // QrScanner's internal state might not be easily accessible.
    // But we are storing `scannerCam` in localStorage.

    let currentCameraId = localStorage.getItem("scannerCam");

    // If not in local storage (first run), or if the stored one isn't actually the active one (edge case),
    // we might default to the first one in the list?
    // Actually, QrScanner defaults to the environment facing camera if available, or just the first one.

    // Let's find the index of the current camera in the list.
    let currentIndex = -1;
    if (currentCameraId) {
      currentIndex = cameras.findIndex((c) => c.id === currentCameraId);
    }

    // If we couldn't find the current one (maybe it wasn't set yet, or device changed), start at 0
    if (currentIndex === -1) {
      // If we don't know which one is active, we can assume it's the first one if we just started.
      // Or better, let's just pick the *next* one from what we *think* it is.
      // If we really don't know, we'll start rotating from 0.
      currentIndex = 0;
    }

    // Calculate next index
    const nextIndex = (currentIndex + 1) % cameras.length;
    const nextCamera = cameras[nextIndex];

    // Save camera preference
    localStorage.setItem("scannerCam", nextCamera.id);

    // Switch to selected camera
    await qrScanner.setCamera(nextCamera.id);

    // Optional: visual feedback
    // console.log(`Switched to camera: ${nextCamera.label || `Camera ${nextIndex + 1}`}`);
    // We could show a toast, but for now just switching is fine.
  } catch (error) {
    console.error("Error switching camera:", error);
    alert("Error switching camera.");
  }
}

// Touch/click handler for clearing status
document
  .getElementById("scannerContainer")
  .addEventListener("click", function (e) {
    // Don't trigger clear if clicking the camera button
    if (e.target.id === "changeCameraBtn") {
      return;
    }
    // If we are touching the video area, we might just want to focus, but here it's used to clear the result overlay
    // The original code prevented default, which might interfere with button clicks if not careful.

    // Only prevent default if we are actually handling the click (e.g. clearing a result)
    if (!isScanning) {
      e.preventDefault();
      clearAndRestart();
    }
  });

// Camera switch button handler
document
  .getElementById("changeCameraBtn")
  .addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    switchCamera();
  });

// Prevent context menu on long press
document.addEventListener("contextmenu", function (e) {
  e.preventDefault();
});

// Initialize when page loads
<<<<<<< HEAD
window.addEventListener("load", function () {
=======
window.addEventListener('load', function() {
>>>>>>> 0d3536d (Move away from inline scripts)
  initScanner();
});

// Cleanup on page unload
window.addEventListener("beforeunload", function () {
  if (qrScanner) {
    qrScanner.destroy();
  }
});
