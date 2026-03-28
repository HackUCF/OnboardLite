// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Collegiate Cyber Defense Club

let scanner;
let isScanning = true;

// ---------------------------------------------------------------------------
// Result handling
// ---------------------------------------------------------------------------

async function onScanResult(result) {
  isScanning = false;

  console.log("Scanned:", result.data);

  try {
    const response = await fetch(
      `/api/member/${encodeURIComponent(result.data)}/dues`,
    );
    const data = await response.json();
    data.dues ? showSuccess() : showError();
  } catch (err) {
    console.error("Error checking dues:", err);
    showError("Network Error");
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
  scanner.start();
}

// ---------------------------------------------------------------------------
// Camera switching
// ---------------------------------------------------------------------------

async function switchCamera() {
  try {
    const cameras = await MiniQrScanner.listCameras();

    if (cameras.length <= 1) {
      alert("Only one camera available");
      return;
    }

    const currentId = scanner._getActiveDeviceId();
    const currentIndex = cameras.findIndex((c) => c.id === currentId);
    const nextIndex = (currentIndex + 1) % cameras.length;

    await scanner.setCamera(cameras[nextIndex].id);
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
  const video = document.getElementById("qr-video");
  scanner = new MiniQrScanner(video, onScanResult, {
    storageKey: "scannerCam",
  });

  try {
    await scanner.start();
  } catch (err) {
    console.error("Camera error:", err);
    showError("Camera Error");
  }
});

window.addEventListener("beforeunload", () => {
  scanner?.stop();
});
