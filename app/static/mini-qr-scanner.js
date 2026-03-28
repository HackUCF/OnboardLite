// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Collegiate Cyber Defense Club

/**
 * MiniQrScanner
 *
 * Shared QR scanning primitive used by both the dues scanner page and the
 * admin roster page. Zero external dependencies at runtime — detection runs
 * via BarcodeDetector (native, Chrome/Android) with a zxing-wasm IIFE fallback
 * for browsers that don't support it. Camera frames are pulled from a <video>
 * element using requestAnimationFrame + an offscreen canvas.
 *
 * Usage:
 *   const scanner = new MiniQrScanner(videoElem, (result) => {
 *     console.log(result.data); // raw QR string
 *   }, { storageKey: "myCamPref" });
 *
 *   await scanner.start();          // opens camera, begins scan loop
 *   scanner.stop();                 // stops stream and loop
 *   await scanner.setCamera(id);    // hot-swap camera without full restart
 *   MiniQrScanner.listCameras();    // => Promise<{ id, label }[]>
 */
class MiniQrScanner {
  /**
   * @param {HTMLVideoElement} videoElem
   * @param {(result: { data: string }) => void} onResult
   * @param {{ storageKey?: string }} [options]
   */
  constructor(videoElem, onResult, { storageKey = "miniQrScannerCam" } = {}) {
    this._video = videoElem;
    this._onResult = onResult;
    this._storageKey = storageKey;

    this._stream = null;
    this._rafId = null;
    this._active = false;
    this._detect = null; // populated once by _buildDetector()

    this._canvas = document.createElement("canvas");
    this._ctx = this._canvas.getContext("2d", { willReadFrequently: true });
  }

  // ---------------------------------------------------------------------------
  // Detection back-ends
  // ---------------------------------------------------------------------------

  async _buildDetector() {
    if (this._detect) return;

    // Path 1: native BarcodeDetector (Chrome 83+, Android WebView, Edge)
    if ("BarcodeDetector" in window) {
      const supported = await BarcodeDetector.getSupportedFormats();
      if (supported.includes("qr_code")) {
        const detector = new BarcodeDetector({ formats: ["qr_code"] });
        this._detect = async (imageData) => {
          const results = await detector.detect(imageData);
          return results.length > 0 ? results[0].rawValue : null;
        };
        return;
      }
    }

    // Path 2: zxing-wasm IIFE fallback — expects window.ZXingWASM to be present
    // (loaded via <script src="https://cdn.jsdelivr.net/npm/zxing-wasm@3.0.0/dist/iife/reader/index.js">)
    if (typeof ZXingWASM === "undefined") {
      throw new Error(
        "MiniQrScanner: ZXingWASM global not found. " +
          "Make sure the zxing-wasm IIFE script is loaded before this file.",
      );
    }

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

    this._detect = async (imageData) => {
      const results = await ZXingWASM.readBarcodes(imageData, {
        formats: ["QRCode"],
        maxNumberOfSymbols: 1,
        tryHarder: false,
      });
      return results.length > 0 ? results[0].text : null;
    };
  }

  // ---------------------------------------------------------------------------
  // Camera stream
  // ---------------------------------------------------------------------------

  async _startStream(deviceId) {
    if (this._stream) {
      this._stream.getTracks().forEach((t) => t.stop());
      this._stream = null;
    }

    if (deviceId) {
      try {
        this._stream = await navigator.mediaDevices.getUserMedia({
          video: { deviceId: { exact: deviceId } },
        });
      } catch (err) {
        if (
          err.name === "OverconstrainedError" ||
          err.name === "NotFoundError"
        ) {
          // Stored device ID is stale — clear it and fall back to default
          localStorage.removeItem(this._storageKey);
          this._stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: "environment" } },
          });
        } else {
          throw err;
        }
      }
    } else {
      this._stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
      });
    }

    this._video.srcObject = this._stream;
    await this._video.play();
  }

  _getActiveDeviceId() {
    if (!this._stream) return null;
    const track = this._stream.getVideoTracks()[0];
    return track ? track.getSettings().deviceId : null;
  }

  // ---------------------------------------------------------------------------
  // Scan loop
  // ---------------------------------------------------------------------------

  _scheduleFrame() {
    this._rafId = requestAnimationFrame(() => this._scanFrame());
  }

  async _scanFrame() {
    if (!this._active) return;

    const v = this._video;
    if (v.readyState >= v.HAVE_ENOUGH_DATA) {
      this._canvas.width = v.videoWidth;
      this._canvas.height = v.videoHeight;
      this._ctx.drawImage(v, 0, 0);

      try {
        const imageData = this._ctx.getImageData(
          0,
          0,
          this._canvas.width,
          this._canvas.height,
        );
        const value = await this._detect(imageData);
        if (value) {
          this._active = false;
          this._onResult({ data: value });
          return; // caller must call start() again to resume
        }
      } catch (err) {
        console.error("MiniQrScanner: scan error", err);
      }
    }

    this._scheduleFrame();
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Build the detector, open the camera, and begin scanning.
   * @param {string|null} [deviceId] - specific camera to open; falls back to
   *   the value saved in localStorage under storageKey, then environment-facing.
   */
  async start(deviceId) {
    await this._buildDetector();
    const id = deviceId ?? localStorage.getItem(this._storageKey) ?? null;
    await this._startStream(id);
    this._active = true;
    this._scheduleFrame();
  }

  /** Stop the scan loop and release the camera stream. */
  stop() {
    this._active = false;
    cancelAnimationFrame(this._rafId);
    if (this._stream) {
      this._stream.getTracks().forEach((t) => t.stop());
      this._stream = null;
    }
    this._video.srcObject = null;
  }

  /**
   * Hot-swap to a different camera without tearing down the detector.
   * Persists the choice to localStorage.
   * @param {string} deviceId
   */
  async setCamera(deviceId) {
    localStorage.setItem(this._storageKey, deviceId);
    const wasActive = this._active;
    this._active = false;
    cancelAnimationFrame(this._rafId);
    await this._startStream(deviceId);
    if (wasActive) {
      this._active = true;
      this._scheduleFrame();
    }
  }

  /**
   * Enumerate available video input devices.
   * @returns {Promise<{ id: string, label: string }[]>}
   */
  static async listCameras() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices
      .filter((d) => d.kind === "videoinput")
      .map((d) => ({ id: d.deviceId, label: d.label }));
  }
}
