import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Compass,
  Navigation,
  Crosshair,
  Camera,
  CameraOff,
  MapPin,
  RefreshCw,
  Trash2,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Leaf,
  Calendar,
  Info,
  Upload,
  Eye,
  X,
  Sparkles,
  ShieldAlert,
  ImageOff,
} from 'lucide-react';
import type { InspectionRecord, DiagnosisResult } from '../types';
import {
  saveFieldInspection,
  fetchFieldInspections,
  diagnoseFieldInspection,
  deleteFieldInspection,
} from '../services/api';

type GpsState = 'idle' | 'requesting' | 'tracking' | 'denied' | 'unavailable' | 'timeout' | 'unsupported';
type CameraState = 'idle' | 'starting' | 'active' | 'denied' | 'unavailable' | 'unsupported';

interface CapturedPhoto {
  rawBlob: Blob;
  overlayBlob: Blob;
  previewUrl: string;
  overlayPreviewUrl: string;
  filename: string;
}

interface InspectionImageProps {
  src?: string | null;
  alt: string;
  className?: string;
  objectFit?: 'cover' | 'contain';
}

const InspectionImage: React.FC<InspectionImageProps> = ({
  src,
  alt,
  className = '',
  objectFit = 'cover',
}) => {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setHasError(false);
  }, [src]);

  if (!src || hasError) {
    return (
      <div
        className={`w-full h-full min-h-[140px] flex flex-col items-center justify-center bg-slate-900/90 text-slate-400 p-4 select-none ${className}`}
      >
        <ImageOff className="w-8 h-8 text-slate-500 mb-1.5" />
        <span className="text-[11px] font-medium text-slate-300">Photograph unavailable</span>
        <span className="text-[10px] text-slate-500">File missing or could not load</span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={`w-full h-full ${objectFit === 'contain' ? 'object-contain' : 'object-cover'} ${className}`}
      loading="lazy"
      onError={() => setHasError(true)}
    />
  );
};

export const FieldInspectionView: React.FC = () => {
  // ── GPS Telemetry State ──────────────────────────────────────────
  const [gpsState, setGpsState] = useState<GpsState>('idle');
  const [coords, setCoords] = useState<{
    latitude: number;
    longitude: number;
    accuracy: number;
    timestamp: number;
  } | null>(null);
  const [gpsErrorMsg, setGpsErrorMsg] = useState<string | null>(null);
  const watchIdRef = useRef<number | null>(null);

  // ── Camera & AR Overlay State ────────────────────────────────────
  const [cameraState, setCameraState] = useState<CameraState>('idle');
  const [cameraErrorMsg, setCameraErrorMsg] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // ── Current Capture & Inspection Input State ─────────────────────
  const [capturedPhoto, setCapturedPhoto] = useState<CapturedPhoto | null>(null);
  const [fieldName, setFieldName] = useState<string>('');
  const [farmerNotes, setFarmerNotes] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // ── Diagnosis Integration State ──────────────────────────────────
  const [isDiagnosing, setIsDiagnosing] = useState<boolean>(false);
  const [activeDiagnosis, setActiveDiagnosis] = useState<DiagnosisResult | null>(null);

  // ── Inspection History State ─────────────────────────────────────
  const [inspections, setInspections] = useState<InspectionRecord[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [selectedInspection, setSelectedInspection] = useState<InspectionRecord | null>(null);

  // ═════════════════════════════════════════════════════════════════
  //  PHASE 11B: GPS GEOLOCATION ENGINE
  // ═════════════════════════════════════════════════════════════════

  const stopGpsTracking = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setGpsState('idle');
  }, []);

  const startGpsTracking = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setGpsState('unsupported');
      setGpsErrorMsg('Geolocation is not supported by your browser.');
      return;
    }

    setGpsState('requesting');
    setGpsErrorMsg(null);

    const options: PositionOptions = {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 0,
    };

    const successCallback: PositionCallback = (pos) => {
      setCoords({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        timestamp: pos.timestamp,
      });
      setGpsState('tracking');
    };

    const errorCallback: PositionErrorCallback = (err) => {
      if (err.code === err.PERMISSION_DENIED) {
        setGpsState('denied');
        setGpsErrorMsg('Location permission denied. Please allow location access in your browser settings.');
      } else if (err.code === err.POSITION_UNAVAILABLE) {
        setGpsState('unavailable');
        setGpsErrorMsg('GPS signal is unavailable. Ensure GPS is enabled or move to an open area.');
      } else if (err.code === err.TIMEOUT) {
        setGpsState('timeout');
        setGpsErrorMsg('GPS request timed out. Retrying satellite lock...');
      } else {
        setGpsState('unavailable');
        setGpsErrorMsg(err.message || 'Unknown GPS error.');
      }
    };

    try {
      watchIdRef.current = navigator.geolocation.watchPosition(
        successCallback,
        errorCallback,
        options
      );
    } catch (e: any) {
      setGpsState('unsupported');
      setGpsErrorMsg(e.message || 'Failed to initialize geolocation.');
    }
  }, []);

  // Cleanup GPS on unmount
  useEffect(() => {
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, []);

  // ═════════════════════════════════════════════════════════════════
  //  PHASE 11C: CAMERA & AR-STYLE VIEWFINDER
  // ═════════════════════════════════════════════════════════════════

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraState('idle');
  }, []);

  const startCamera = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraState('unsupported');
      setCameraErrorMsg('Camera access is not supported by this browser. Use photo upload instead.');
      return;
    }

    setCameraState('starting');
    setCameraErrorMsg(null);

    try {
      // Prefer rear environment-facing camera on mobile
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraState('active');
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraState('denied');
        setCameraErrorMsg('Camera permission denied. Please enable camera access in your browser settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraState('unavailable');
        setCameraErrorMsg('No camera device found. Please attach a camera or use file upload.');
      } else {
        setCameraState('unavailable');
        setCameraErrorMsg(`Camera error: ${err.message || 'Could not start camera feed.'}`);
      }
    }
  };

  // Cleanup camera stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Burn visible GPS metadata onto exported overlay photo
  const createOverlayImage = (
    baseCanvas: HTMLCanvasElement,
    lat: number,
    lon: number,
    acc: number,
    ts: string,
    fName: string
  ): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      const w = baseCanvas.width;
      const h = baseCanvas.height;

      const overlayCanvas = document.createElement('canvas');
      overlayCanvas.width = w;
      overlayCanvas.height = h;
      const ctx = overlayCanvas.getContext('2d');
      if (!ctx) {
        return baseCanvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Canvas export failed'))));
      }

      // Draw original camera frame
      ctx.drawImage(baseCanvas, 0, 0);

      // Draw bottom AR metadata banner
      const bannerHeight = Math.max(70, Math.floor(h * 0.12));
      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)'; // Slate 900 with transparency
      ctx.fillRect(0, h - bannerHeight, w, bannerHeight);

      // Accent border
      ctx.fillStyle = '#10b981'; // Emerald 500
      ctx.fillRect(0, h - bannerHeight, w, 3);

      // Text styling
      const fontSize = Math.max(12, Math.floor(bannerHeight * 0.22));
      ctx.font = `600 ${fontSize}px sans-serif`;
      ctx.fillStyle = '#ffffff';

      const paddingX = Math.max(16, Math.floor(w * 0.03));
      const line1Y = h - bannerHeight + fontSize * 1.5;
      const line2Y = h - bannerHeight + fontSize * 3.1;

      // Line 1: Coordinates + Accuracy
      const latStr = `${Math.abs(lat).toFixed(6)}° ${lat >= 0 ? 'N' : 'S'}`;
      const lonStr = `${Math.abs(lon).toFixed(6)}° ${lon >= 0 ? 'E' : 'W'}`;
      const accStr = acc > 0 ? `(±${acc.toFixed(1)}m)` : '';
      ctx.fillText(`📍 GPS: ${latStr}, ${lonStr} ${accStr}`, paddingX, line1Y);

      // Line 2: Timestamp + Field Tag + PlantCare watermark
      ctx.font = `400 ${fontSize * 0.85}px sans-serif`;
      ctx.fillStyle = '#94a3b8'; // Slate 400
      const tagText = fName ? `[${fName}] • ` : '';
      ctx.fillText(`${tagText}${ts} • PlantCare AR Field Inspector`, paddingX, line2Y);

      overlayCanvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error('Failed to create overlay image blob'));
        },
        'image/jpeg',
        0.92
      );
    });
  };

  // Capture frame from active video feed
  const handleCaptureFrame = async () => {
    if (!videoRef.current || cameraState !== 'active') return;

    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (rawBlob) => {
      if (!rawBlob) return;

      const lat = coords?.latitude || 0;
      const lon = coords?.longitude || 0;
      const acc = coords?.accuracy || 0;
      const nowStr = new Date().toLocaleString();

      const overlayBlob = await createOverlayImage(canvas, lat, lon, acc, nowStr, fieldName);

      const rawUrl = URL.createObjectURL(rawBlob);
      const overlayUrl = URL.createObjectURL(overlayBlob);

      setCapturedPhoto({
        rawBlob,
        overlayBlob,
        previewUrl: rawUrl,
        overlayPreviewUrl: overlayUrl,
        filename: `capture_${Date.now()}.jpg`,
      });

      // Stop camera once photo is taken to preserve battery
      stopCamera();
    }, 'image/jpeg', 0.95);
  };

  // File Upload Fallback
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const rawBlob = file;
    const rawUrl = URL.createObjectURL(rawBlob);

    // If GPS is active, burn overlay metadata onto uploaded photo
    const img = new Image();
    img.src = rawUrl;
    img.onload = async () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth || 1280;
      canvas.height = img.naturalHeight || 720;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(img, 0, 0);
        const lat = coords?.latitude || 0;
        const lon = coords?.longitude || 0;
        const acc = coords?.accuracy || 0;
        const nowStr = new Date().toLocaleString();
        const overlayBlob = await createOverlayImage(canvas, lat, lon, acc, nowStr, fieldName);
        const overlayUrl = URL.createObjectURL(overlayBlob);

        setCapturedPhoto({
          rawBlob,
          overlayBlob,
          previewUrl: rawUrl,
          overlayPreviewUrl: overlayUrl,
          filename: file.name,
        });
      }
    };
  };

  const handleRetake = () => {
    if (capturedPhoto) {
      URL.revokeObjectURL(capturedPhoto.previewUrl);
      URL.revokeObjectURL(capturedPhoto.overlayPreviewUrl);
      setCapturedPhoto(null);
    }
    setActiveDiagnosis(null);
    setSaveSuccessMsg(null);
    startCamera();
  };

  // ═════════════════════════════════════════════════════════════════
  //  PHASE 11D: SAVE INSPECTION RECORDS
  // ═════════════════════════════════════════════════════════════════

  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const records = await fetchFieldInspections();
      setInspections(records);
    } catch (err: any) {
      console.error('Failed to load field inspection history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleSaveInspection = async () => {
    if (!capturedPhoto) return;

    if (!coords) {
      alert('GPS location is required before saving a field inspection. Please click "Start GPS Tracking".');
      return;
    }

    setIsSaving(true);
    setSaveSuccessMsg(null);

    try {
      const formData = new FormData();
      formData.append('file', capturedPhoto.rawBlob, capturedPhoto.filename);
      formData.append('overlay_file', capturedPhoto.overlayBlob, `overlay_${capturedPhoto.filename}`);
      formData.append('latitude', coords.latitude.toString());
      formData.append('longitude', coords.longitude.toString());
      formData.append('gps_accuracy', coords.accuracy.toString());
      formData.append('field_name', fieldName.trim());
      formData.append('notes', farmerNotes.trim());
      formData.append('timestamp', new Date().toLocaleString());

      const res = await saveFieldInspection(formData);
      setSaveSuccessMsg(`Inspection saved successfully with ID #${res.inspection_id}`);

      // Refresh history log
      await loadHistory();
      setSelectedInspection(res.inspection);
    } catch (err: any) {
      alert(`Failed to save field inspection: ${err.message || 'Server error'}`);
    } finally {
      setIsSaving(false);
    }
  };

  // ═════════════════════════════════════════════════════════════════
  //  PHASE 11E: OPTIONAL DISEASE INTEGRATION
  // ═════════════════════════════════════════════════════════════════

  const handleDiagnoseCurrent = async () => {
    if (!selectedInspection && !capturedPhoto) return;

    setIsDiagnosing(true);
    try {
      let inspId = selectedInspection?.inspection_id;

      // If user hasn't saved yet, save automatically first
      if (!inspId && capturedPhoto && coords) {
        const formData = new FormData();
        formData.append('file', capturedPhoto.rawBlob, capturedPhoto.filename);
        formData.append('overlay_file', capturedPhoto.overlayBlob, `overlay_${capturedPhoto.filename}`);
        formData.append('latitude', coords.latitude.toString());
        formData.append('longitude', coords.longitude.toString());
        formData.append('gps_accuracy', coords.accuracy.toString());
        formData.append('field_name', fieldName.trim() || 'Quick Field Scan');
        formData.append('notes', farmerNotes.trim());
        formData.append('timestamp', new Date().toLocaleString());

        const saveRes = await saveFieldInspection(formData);
        inspId = saveRes.inspection_id;
        setSelectedInspection(saveRes.inspection);
      }

      if (!inspId) {
        alert('Please enable GPS and capture or save an inspection before analyzing.');
        return;
      }

      const diagRes = await diagnoseFieldInspection(inspId);
      setActiveDiagnosis(diagRes.diagnosis);
      setSelectedInspection(diagRes.inspection);
      await loadHistory();
    } catch (err: any) {
      alert(`Diagnosis failed: ${err.message || 'Server error'}`);
    } finally {
      setIsDiagnosing(false);
    }
  };

  const handleDeleteInspection = async (id: number) => {
    if (!confirm(`Are you sure you want to delete inspection record #${id}?`)) return;
    try {
      await deleteFieldInspection(id);
      if (selectedInspection?.inspection_id === id) {
        setSelectedInspection(null);
      }
      await loadHistory();
    } catch (err: any) {
      alert(`Failed to delete record: ${err.message}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 mb-2">
          <Compass className="w-3.5 h-3.5 text-emerald-600 animate-spin-slow" />
          <span>Stage 11 Geospatial AR Field Inspection</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Geospatial AR Field Inspector
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Perform live field scouting, acquire GPS-tagged leaf photographs, view real-time AR-style HUD metadata,
          and run instant plant disease diagnostics.
        </p>
      </div>

      {/* Main Grid: Left = Camera & AR Viewfinder, Right = Telemetry & Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column (Cols 1-7): Camera & AR Viewfinder */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-3xl border border-slate-200/80 p-4 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <Camera className="w-4 h-4 text-emerald-600" />
                <span>AR-Style Viewfinder HUD</span>
              </h2>

              <span className="text-[11px] font-medium text-slate-400">
                2D Sensor HUD Overlay
              </span>
            </div>

            {/* Viewfinder Frame Container */}
            <div className="relative w-full aspect-[4/3] sm:aspect-[16/10] bg-slate-950 rounded-2xl overflow-hidden shadow-inner flex items-center justify-center border border-slate-800">
              {/* Active Video Stream */}
              <video
                ref={videoRef}
                playsInline
                muted
                autoPlay
                className={`w-full h-full object-cover ${
                  cameraState === 'active' && !capturedPhoto ? 'block' : 'hidden'
                }`}
              />

              {/* Captured Photo Preview */}
              {capturedPhoto && (
                <img
                  src={capturedPhoto.overlayPreviewUrl}
                  alt="Captured inspection"
                  className="w-full h-full object-contain bg-black"
                />
              )}

              {/* Idle / Camera Off State */}
              {cameraState !== 'active' && !capturedPhoto && (
                <div className="text-center p-6 space-y-3">
                  <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
                    <CameraOff className="w-7 h-7" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-slate-200">Camera Feed Inactive</p>
                    <p className="text-[11px] text-slate-400 max-w-xs">
                      Click &quot;Start Camera Feed&quot; below to launch the live viewfinder, or upload a leaf photograph.
                    </p>
                  </div>
                  {cameraErrorMsg && (
                    <div className="p-2.5 rounded-xl bg-rose-950/60 border border-rose-800 text-[11px] text-rose-300 max-w-sm mx-auto flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                      <span>{cameraErrorMsg}</span>
                    </div>
                  )}
                </div>
              )}

              {/* AR-Style HUD Graphics (Visible when Camera is Active & not yet captured) */}
              {cameraState === 'active' && !capturedPhoto && (
                <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between">
                  {/* Top HUD Bar */}
                  <div className="flex items-center justify-between text-[11px] text-emerald-400 font-mono drop-shadow-md">
                    <div className="bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-emerald-500/40 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <span>LIVE HUD</span>
                    </div>

                    <div className="bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-full border border-emerald-500/40">
                      {coords ? (
                        <span>
                          ±{coords.accuracy.toFixed(0)}m ACCURACY
                        </span>
                      ) : (
                        <span className="text-amber-400">GPS STANDBY</span>
                      )}
                    </div>
                  </div>

                  {/* Center Target Framing Reticle */}
                  <div className="relative self-center w-48 h-48 sm:w-60 sm:h-60 flex items-center justify-center">
                    {/* Corner Framing Brackets */}
                    <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-emerald-400/80 rounded-tl-sm" />
                    <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-emerald-400/80 rounded-tr-sm" />
                    <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-emerald-400/80 rounded-bl-sm" />
                    <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-emerald-400/80 rounded-br-sm" />

                    {/* Center Crosshair */}
                    <Crosshair className="w-8 h-8 text-emerald-400/60" />
                    <span className="absolute bottom-2 text-[10px] text-emerald-400/80 font-mono tracking-widest uppercase">
                      Center Leaf
                    </span>
                  </div>

                  {/* Bottom Telemetry HUD Bar */}
                  <div className="bg-slate-900/85 backdrop-blur-md p-2.5 rounded-xl border border-emerald-500/40 text-[11px] font-mono text-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-1 shadow-lg">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                      {coords ? (
                        <span>
                          LAT {coords.latitude.toFixed(6)}° • LON {coords.longitude.toFixed(6)}°
                        </span>
                      ) : (
                        <span className="text-amber-400">Start GPS tracking for telemetry burn</span>
                      )}
                    </div>
                    <span className="text-slate-400 text-[10px]">
                      {new Date().toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Viewfinder Action Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <div className="flex items-center gap-2">
                {cameraState !== 'active' && !capturedPhoto && (
                  <button
                    onClick={startCamera}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white shadow-xs hover:bg-emerald-700 active:scale-95 transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Start Camera Feed</span>
                  </button>
                )}

                {cameraState === 'active' && !capturedPhoto && (
                  <>
                    <button
                      onClick={handleCaptureFrame}
                      className="px-5 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 text-white shadow-md hover:bg-emerald-700 active:scale-95 transition-all flex items-center gap-2 cursor-pointer animate-pulse"
                    >
                      <Crosshair className="w-4 h-4" />
                      <span>Capture Leaf Photo</span>
                    </button>
                    <button
                      onClick={stopCamera}
                      className="px-3.5 py-2 rounded-xl text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
                    >
                      Stop Camera
                    </button>
                  </>
                )}

                {capturedPhoto && (
                  <button
                    onClick={handleRetake}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-white shadow-xs hover:bg-slate-900 transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retake Photo</span>
                  </button>
                )}
              </div>

              {/* File Upload Fallback */}
              <label className="px-3.5 py-2 rounded-xl text-xs font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5 cursor-pointer">
                <Upload className="w-3.5 h-3.5 text-slate-500" />
                <span>Upload Photo Fallback</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        </div>

        {/* Right Column (Cols 8-12): GPS Telemetry, Metadata Form, & Actions */}
        <div className="lg:col-span-5 space-y-6">
          {/* Phase 11B: GPS Location Card */}
          <div className="bg-white rounded-3xl border border-slate-200/80 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                    gpsState === 'tracking'
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  <Navigation className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                    Live Geolocation Telemetry
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Browser GPS API with high-accuracy mode
                  </p>
                </div>
              </div>

              {/* GPS Status Indicator */}
              {gpsState === 'tracking' ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  Active Fix
                </span>
              ) : gpsState === 'requesting' ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-100 text-amber-800">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Requesting...
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600">
                  Standby
                </span>
              )}
            </div>

            {/* Coordinates Display Box */}
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
              {coords ? (
                <div className="space-y-1.5 font-mono text-xs text-slate-800">
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-sans text-[11px]">Latitude:</span>
                    <span className="font-semibold text-slate-900">{coords.latitude.toFixed(6)}°</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-sans text-[11px]">Longitude:</span>
                    <span className="font-semibold text-slate-900">{coords.longitude.toFixed(6)}°</span>
                  </div>
                  <div className="flex justify-between items-center pt-1 border-t border-slate-200">
                    <span className="text-slate-500 font-sans text-[11px]">Reported Accuracy:</span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/70">
                      ±{coords.accuracy.toFixed(1)} metres
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-center py-3 text-xs text-slate-500">
                  {gpsErrorMsg ? (
                    <span className="text-rose-600 font-medium">{gpsErrorMsg}</span>
                  ) : (
                    <span>GPS telemetry is currently off. Click &quot;Start Tracking&quot; to acquire live coordinates.</span>
                  )}
                </div>
              )}
            </div>

            {/* Honest Accuracy Advisory */}
            <div className="p-2.5 rounded-xl bg-amber-50/70 border border-amber-200/80 text-[11px] text-amber-900 leading-relaxed flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
              <span>
                <strong>GPS Accuracy Notice:</strong> Coordinates are derived from your device&apos;s GPS sensor
                (consumer accuracy typically ±5 to ±25m). Not certified for cadastral or survey-grade boundary measurements.
              </span>
            </div>

            {/* GPS Tracking Controls */}
            <div className="flex items-center gap-2">
              {gpsState !== 'tracking' ? (
                <button
                  onClick={startGpsTracking}
                  className="w-full py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 text-white shadow-xs hover:bg-emerald-700 active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Navigation className="w-3.5 h-3.5" />
                  <span>Start GPS Tracking</span>
                </button>
              ) : (
                <button
                  onClick={stopGpsTracking}
                  className="w-full py-2.5 rounded-xl text-xs font-semibold bg-slate-800 text-white shadow-xs hover:bg-slate-900 transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <span>Stop GPS Tracking</span>
                </button>
              )}
            </div>
          </div>

          {/* Inspection Metadata Form & Save Actions */}
          <div className="bg-white rounded-3xl border border-slate-200/80 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
              <Leaf className="w-4 h-4 text-emerald-600" />
              <span>Field Inspection Details</span>
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Field / Plot Identifier (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. North Plot - Block 2"
                  value={fieldName}
                  onChange={(e) => setFieldName(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-500 bg-slate-50 focus:bg-white transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Agronomic Observations & Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Mild chlorotic spots on lower foliage after 3 days of high humidity..."
                  value={farmerNotes}
                  onChange={(e) => setFarmerNotes(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-500 bg-slate-50 focus:bg-white transition-colors resize-none"
                />
              </div>
            </div>

            {/* Action Buttons: Save & Diagnose */}
            <div className="pt-2 space-y-2">
              <button
                onClick={handleSaveInspection}
                disabled={!capturedPhoto || isSaving}
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-slate-900 text-white shadow-xs hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                {isSaving ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving Inspection Record...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Save Inspection Record</span>
                  </>
                )}
              </button>

              <button
                onClick={handleDiagnoseCurrent}
                disabled={!capturedPhoto || isDiagnosing}
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-emerald-600 text-white shadow-md hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                {isDiagnosing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Running EfficientNet-B0 Inference...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-emerald-200 animate-pulse" />
                    <span>Analyse Leaf Condition (Phase 11E)</span>
                  </>
                )}
              </button>

              {saveSuccessMsg && (
                <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-[11px] text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>{saveSuccessMsg}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Phase 11E: Real-Time Diagnosis Result Banner (If run) */}
      {activeDiagnosis && (
        <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200/80">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
                <Leaf className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Field Diagnosis Result (EfficientNet-B0)
                </h3>
                <p className="text-xs text-slate-500">
                  Condition: <strong>{activeDiagnosis.crop} — {activeDiagnosis.disease}</strong>
                </p>
              </div>
            </div>

            <span
              className={`px-3 py-1 rounded-full text-xs font-bold ${
                activeDiagnosis.is_healthy
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-rose-100 text-rose-800'
              }`}
            >
              {activeDiagnosis.confidence.toFixed(1)}% Confidence
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Estimated Severity
              </span>
              <span className="text-sm font-bold text-slate-800 mt-1 block">
                {activeDiagnosis.severity.level}
              </span>
              <span className="text-xs text-slate-500">
                {activeDiagnosis.severity.affected_percentage !== null
                  ? `${activeDiagnosis.severity.affected_percentage}% visual leaf damage`
                  : 'Surface clear'}
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 md:col-span-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Immediate Action Recommendation
              </span>
              <p className="text-xs text-slate-700 mt-1 leading-relaxed">
                {activeDiagnosis.treatment?.recommended_action || 'No immediate chemical action required.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Phase 11D: Historical Field Inspection Log */}
      <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-emerald-600" />
              <span>Inspection History & Geotagged Records</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Historical GPS logs with captured photographs and diagnostic assessments.
            </p>
          </div>

          <button
            onClick={loadHistory}
            disabled={isLoadingHistory}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors flex items-center gap-1.5 self-start cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingHistory ? 'animate-spin' : ''}`} />
            <span>Refresh Log</span>
          </button>
        </div>

        {/* Inspections Grid */}
        {inspections.length === 0 ? (
          <div className="text-center py-16 px-4 border-2 border-dashed border-slate-200/90 rounded-3xl bg-slate-50/50 space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-center mx-auto text-slate-400">
              <Compass className="w-7 h-7 text-emerald-600" />
            </div>
            <div className="space-y-1.5 max-w-md mx-auto">
              <h3 className="text-base font-bold text-slate-900">No field inspections yet</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Your GPS-tagged field inspections will appear here after you capture and save your first inspection.
              </p>
            </div>
            <button
              onClick={() => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
                if (cameraState !== 'active' && !capturedPhoto) {
                  startCamera();
                }
              }}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 active:scale-95 transition-all cursor-pointer"
            >
              <Camera className="w-4 h-4" />
              <span>Start New Field Inspection</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {inspections.map((insp) => (
              <div
                key={insp.inspection_id}
                className="rounded-2xl border border-slate-200/80 bg-slate-50/50 hover:bg-white hover:shadow-md transition-all overflow-hidden flex flex-col justify-between"
              >
                {/* Photo Thumbnail */}
                <div className="relative aspect-[16/9] bg-slate-900 overflow-hidden">
                  <InspectionImage
                    src={insp.overlay_image_url || insp.image_url}
                    alt={`Inspection #${insp.inspection_id}`}
                    objectFit="cover"
                  />
                  <div className="absolute top-2 left-2 bg-slate-900/80 backdrop-blur-md px-2.5 py-0.5 rounded-full text-[10px] font-mono text-emerald-400 border border-emerald-500/30">
                    #{insp.inspection_id}
                  </div>
                  {insp.disease && (
                    <div
                      className={`absolute top-2 right-2 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        insp.disease.toLowerCase() === 'healthy'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-rose-600 text-white'
                      }`}
                    >
                      {insp.crop} — {insp.disease}
                    </div>
                  )}
                </div>

                {/* Details Content */}
                <div className="p-4 space-y-2.5 flex-1 flex flex-col justify-between text-xs">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-slate-500 text-[11px]">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {insp.timestamp}
                      </span>
                      <span className="font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                        ±{insp.gps_accuracy}m
                      </span>
                    </div>

                    {insp.field_name && (
                      <p className="font-bold text-slate-900 text-xs">
                        {insp.field_name}
                      </p>
                    )}

                    <div className="font-mono text-[11px] text-slate-600">
                      Lat: {insp.latitude.toFixed(6)}°, Lon: {insp.longitude.toFixed(6)}°
                    </div>

                    {insp.notes && (
                      <p className="text-[11px] text-slate-500 italic line-clamp-2">
                        &quot;{insp.notes}&quot;
                      </p>
                    )}
                  </div>

                  {/* Actions Footer */}
                  <div className="pt-3 border-t border-slate-200/60 flex items-center justify-between gap-2">
                    <a
                      href={`https://www.google.com/maps?q=${insp.latitude},${insp.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-teal-600 hover:text-teal-700 font-semibold flex items-center gap-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span>View on Maps</span>
                    </a>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setSelectedInspection(insp)}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Inspect</span>
                      </button>

                      <button
                        onClick={() => handleDeleteInspection(insp.inspection_id)}
                        className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                        title="Delete record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Inspection Modal / Drawer */}
      {selectedInspection && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Navigation className="w-4 h-4 text-emerald-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Inspection Record #{selectedInspection.inspection_id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedInspection(null)}
                className="p-1.5 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Photo preview with overlay */}
            <div className="rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 aspect-video">
              <InspectionImage
                src={selectedInspection.overlay_image_url || selectedInspection.image_url}
                alt="Field record"
                objectFit="contain"
              />
            </div>

            {/* Metadata Summary */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[11px] text-slate-400 block font-medium">GPS Telemetry</span>
                <span className="font-mono font-semibold text-slate-900 block mt-0.5">
                  {selectedInspection.latitude.toFixed(6)}°, {selectedInspection.longitude.toFixed(6)}°
                </span>
                <span className="text-[10px] text-emerald-700">Accuracy: ±{selectedInspection.gps_accuracy}m</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[11px] text-slate-400 block font-medium">Field / Timestamp</span>
                <span className="font-semibold text-slate-900 block mt-0.5">
                  {selectedInspection.field_name || 'Unassigned Field'}
                </span>
                <span className="text-[10px] text-slate-500">{selectedInspection.timestamp}</span>
              </div>
            </div>

            {selectedInspection.notes && (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                <span className="text-[11px] text-slate-400 block font-medium mb-1">Farmer Notes</span>
                <p className="text-slate-700 leading-relaxed">{selectedInspection.notes}</p>
              </div>
            )}

            {/* Diagnosis Status */}
            {selectedInspection.disease ? (
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-emerald-900">
                    Diagnosed: {selectedInspection.crop} — {selectedInspection.disease}
                  </span>
                  <span className="text-emerald-700 font-semibold">
                    {selectedInspection.prediction_confidence}% Confidence
                  </span>
                </div>
                <p className="text-[11px] text-emerald-800">
                  Severity: <strong>{selectedInspection.severity}</strong> (
                  {selectedInspection.affected_area_percentage}% visual damaged area)
                </p>
                {selectedInspection.treatment_summary && (
                  <p className="text-[11px] text-slate-600 pt-1 border-t border-emerald-200/70">
                    <strong>Treatment Action:</strong> {selectedInspection.treatment_summary}
                  </p>
                )}
              </div>
            ) : (
              <button
                onClick={() => handleDiagnoseCurrent()}
                disabled={isDiagnosing}
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{isDiagnosing ? 'Analyzing...' : 'Run EfficientNet-B0 Disease Diagnosis'}</span>
              </button>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <a
                href={`https://www.google.com/maps?q=${selectedInspection.latitude},${selectedInspection.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors flex items-center gap-1.5"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open in Google Maps</span>
              </a>
              <button
                onClick={() => setSelectedInspection(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
