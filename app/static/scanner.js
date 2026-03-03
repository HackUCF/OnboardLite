/**
 * Dues Scanner
 *
 * Detection strategy (in order):
 *   1. BarcodeDetector (native browser API — Chrome/Android, fast, zero extra cost)
 *   2. zxing-wasm       (WASM build of ZXing-C++, cross-browser fallback)
 *
 * Camera frames are grabbed via requestAnimationFrame against a <video> element.
 * No third-party camera/scanner library is used — just getUserMedia + canvas.
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let stream = null; // MediaStream from getUserMedia
let rafId = null; // requestAnimationFrame handle
let isScanning = true; // false while showing a result

// Offscreen canvas used to snapshot frames for both detection paths
const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d", { willReadFrequently: true });

// ---------------------------------------------------------------------------
// Detection back-ends
// ---------------------------------------------------------------------------

// Will be resolved to a function (ImageData) => Promise<string|null>
let detect = null;

async function buildDetector() {
  // --- Path 1: native BarcodeDetector ---
  if ("BarcodeDetector" in window) {
    const supported = await BarcodeDetector.getSupportedFormats();
    if (supported.includes("qr_code")) {
      const detector = new BarcodeDetector({ formats: ["qr_code"] });
      return async (imageData) => {
        const results = await detector.detect(imageData);
        return results.length > 0 ? results[0].rawValue : null;
      };
    }
  }

  // --- Path 2: zxing-wasm IIFE fallback ---
  // The IIFE script registers itself as window.ZXingWASM
  if (typeof ZXingWASM === "undefined") {
    throw new Error("ZXingWASM not loaded");
  }

  // Point the WASM loader at the jsDelivr CDN so we never vendor the binary
  ZXingWASM.prepareZXingModule({
    overrides: {
      locateFile: (path, prefix) => {
        if (path.endsWith(".wasm")) {
          return `https://cdn.jsdelivr.net/npm/zxing-wasm@3.0.0/dist/reader/${path}`;
        }
        return prefix + path;
      },
    },
  });

  return async (imageData) => {
    const results = await ZXingWASM.readBarcodes(imageData, {
      formats: ["QRCode"],
      maxNumberOfSymbols: 1,
      tryHarder: false,
    });
    return results.length > 0 ? results[0].text : null;
  };
}

// ---------------------------------------------------------------------------
// Camera
// ---------------------------------------------------------------------------

const video = document.getElementById("qr-video");

async function startCamera(deviceId) {
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
  }

  if (deviceId) {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: deviceId } },
      });
    } catch (err) {
      if (err.name === "OverconstrainedError" || err.name === "NotFoundError") {
        // Saved device ID is stale — clear it and fall back to default
        localStorage.removeItem("scannerCam");
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
        });
      } else {
        throw err;
      }
    }
  } else {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
    });
  }

  video.srcObject = stream;
  await video.play();
}

function getActiveDeviceId() {
  if (!stream) return null;
  const track = stream.getVideoTracks()[0];
  return track ? track.getSettings().deviceId : null;
}

// ---------------------------------------------------------------------------
// Scan loop
// ---------------------------------------------------------------------------

function scheduleNextFrame() {
  rafId = requestAnimationFrame(scanFrame);
}

async function scanFrame() {
  if (!isScanning || video.readyState < video.HAVE_ENOUGH_DATA) {
    scheduleNextFrame();
    return;
  }

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.drawImage(video, 0, 0);

  try {
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const value = await detect(imageData);
    if (value) {
      await onScanResult(value);
      return; // don't schedule another frame — wait for user to clear
    }
  } catch (err) {
    console.error("Scan error:", err);
  }

  scheduleNextFrame();
}

// ---------------------------------------------------------------------------
// Result handling
// ---------------------------------------------------------------------------

async function onScanResult(value) {
  isScanning = false;
  cancelAnimationFrame(rafId);

  console.log("Scanned:", value);

  try {
    const response = await fetch(
      `/api/member/${encodeURIComponent(value)}/dues`,
    );
    const data = await response.json();
    data.dues ? showSuccess() : showError();
  } catch (err) {
    console.error("Error checking dues:", err);
    showError("Network Error", "Could not reach server");
  }
}

function showSuccess() {
  const container = document.getElementById("scannerContainer");
  const statusMessage = document.getElementById("statusMessage");
  const clearInstruction = document.getElementById("clearInstruction");

  container.className = "scanner-container success";
  statusMessage.textContent = "Dues Paid ✓";
  statusMessage.classList.add("show");
  clearInstruction.classList.add("show");
}

function showError(title = "Dues Not Paid ✗") {
  const container = document.getElementById("scannerContainer");
  const statusMessage = document.getElementById("statusMessage");
  const clearInstruction = document.getElementById("clearInstruction");

  container.className = "scanner-container error";
  statusMessage.textContent = title;
  statusMessage.classList.add("show");
  clearInstruction.classList.add("show");
}

function clearAndRestart() {
  if (isScanning) return;

  const container = document.getElementById("scannerContainer");
  const statusMessage = document.getElementById("statusMessage");
  const clearInstruction = document.getElementById("clearInstruction");

  container.className = "scanner-container";
  statusMessage.classList.remove("show");
  clearInstruction.classList.remove("show");

  isScanning = true;
  scheduleNextFrame();
}

// ---------------------------------------------------------------------------
// Camera switching
// ---------------------------------------------------------------------------

async function switchCamera() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter((d) => d.kind === "videoinput");

    if (cameras.length <= 1) {
      alert("Only one camera available");
      return;
    }

    const currentId = getActiveDeviceId();
    const currentIndex = cameras.findIndex((c) => c.deviceId === currentId);
    const nextIndex = (currentIndex + 1) % cameras.length;
    const nextId = cameras[nextIndex].deviceId;

    localStorage.setItem("scannerCam", nextId);
    await startCamera(nextId);
  } catch (err) {
    console.error("Error switching camera:", err);
    alert("Error switching camera.");
  }
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

document.getElementById("scannerContainer").addEventListener("click", (e) => {
  if (e.target.id === "changeCameraBtn") return;
  if (!isScanning) {
    e.preventDefault();
    clearAndRestart();
  }
});

document.getElementById("changeCameraBtn").addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  switchCamera();
});

document.addEventListener("contextmenu", (e) => e.preventDefault());

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

window.addEventListener("load", async () => {
  try {
    detect = await buildDetector();
  } catch (err) {
    console.error("Failed to build barcode detector:", err);
    showError("Scanner unavailable");
    return;
  }

  const savedCamera = localStorage.getItem("scannerCam");
  try {
    await startCamera(savedCamera || null);
  } catch (err) {
    console.error("Camera error:", err);
    showError("Camera Error", "Unable to access camera");
    return;
  }

  scheduleNextFrame();
});

window.addEventListener("beforeunload", () => {
  cancelAnimationFrame(rafId);
  if (stream) stream.getTracks().forEach((t) => t.stop());
});
