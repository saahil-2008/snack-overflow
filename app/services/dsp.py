# app/services/dsp.py — SonicAssay signal processing pipeline (Section 4.3.4)
import io
import struct
import wave
from typing import Any

import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert

from app.core.errors import ApiError


def validate_wav(raw: bytes) -> tuple[np.ndarray, int]:
    """Decode & validate RIFF PCM 16-bit mono WAV. Returns (float samples in [-1,1], sample_rate)."""
    try:
        buf = io.BytesIO(raw)
        with wave.open(buf, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sr = wf.getframerate()
            nframes = wf.getnframes()
            frames = wf.readframes(nframes)
    except Exception as e:
        raise ApiError(415, "AUDIO_FORMAT_UNSUPPORTED",
                       "Cannot decode WAV file",
                       {"receivedContentType": "audio/wav", "reason": str(e)})

    if channels != 1:
        raise ApiError(415, "AUDIO_FORMAT_UNSUPPORTED",
                       "Audio must be mono",
                       {"receivedContentType": "audio/wav", "reason": f"Got {channels} channels, expected 1"})
    if sampwidth != 2:
        raise ApiError(415, "AUDIO_FORMAT_UNSUPPORTED",
                       "Audio must be 16-bit PCM",
                       {"receivedContentType": "audio/wav", "reason": f"Got {sampwidth*8}-bit, expected 16-bit"})
    if sr not in (44100, 48000):
        raise ApiError(415, "AUDIO_FORMAT_UNSUPPORTED",
                       "Sample rate must be 44100 or 48000 Hz",
                       {"receivedContentType": "audio/wav", "reason": f"Got {sr} Hz"})

    duration = nframes / sr
    if duration < 3.0 or duration > 15.0:
        raise ApiError(415, "AUDIO_FORMAT_UNSUPPORTED",
                       f"Duration must be 3–15 s, got {duration:.1f} s",
                       {"receivedContentType": "audio/wav", "reason": f"Duration {duration:.1f}s outside 3-15s range"})

    # Convert to float [-1, 1]
    samples = np.array(struct.unpack(f"<{nframes}h", frames), dtype=np.float64) / 32768.0
    return samples, sr


def _bandpass(samples: np.ndarray, sr: int) -> np.ndarray:
    """4th-order Butterworth band-pass 80–3000 Hz, zero-phase."""
    nyq = sr / 2
    low = 80 / nyq
    high = min(3000 / nyq, 0.99)
    sos = butter(4, [low, high], btype="band", output="sos")
    return sosfiltfilt(sos, samples)


def _noise_floor(filtered: np.ndarray, sr: int) -> tuple[float, np.ndarray]:
    """Compute noise RMS and mean noise magnitude spectrum from the first 1.5 s."""
    n_silence = int(1.5 * sr)
    silence = filtered[:n_silence]
    noise_rms = float(np.sqrt(np.mean(silence ** 2)))
    if noise_rms == 0:
        noise_rms = 1e-10

    # Mean magnitude spectrum of 40 ms Hann frames over silence
    frame_len = int(0.040 * sr)
    n_fft = 8192
    hop = frame_len // 2
    spectra = []
    for start in range(0, len(silence) - frame_len, hop):
        frame = silence[start:start + frame_len]
        windowed = frame * np.hanning(frame_len)
        padded = np.zeros(n_fft)
        padded[:frame_len] = windowed
        mag = np.abs(np.fft.rfft(padded))
        spectra.append(mag)

    if spectra:
        noise_spectrum = np.mean(spectra, axis=0)
    else:
        noise_spectrum = np.zeros(n_fft // 2 + 1)

    return noise_rms, noise_spectrum


def _detect_impacts(filtered: np.ndarray, sr: int, noise_rms: float) -> list[int]:
    """TAP impact detection after 1.5 s. Returns onset sample indices."""
    start_sample = int(1.5 * sr)
    signal = filtered[start_sample:]
    if len(signal) == 0:
        return []

    # Frame RMS with 5 ms window / 2.5 ms hop
    frame_size = int(0.005 * sr)
    hop = int(0.0025 * sr)
    threshold = 5 * noise_rms
    skip_samples = int(0.250 * sr)  # 250 ms after each onset

    onsets = []
    i = 0
    while i < len(signal) - frame_size:
        frame_rms = np.sqrt(np.mean(signal[i:i + frame_size] ** 2))
        if frame_rms > threshold:
            onsets.append(start_sample + i)
            if len(onsets) >= 3:
                break
            i += skip_samples
        else:
            i += hop

    return onsets


def _impact_features(samples: np.ndarray, onset: int, sr: int,
                     noise_spectrum: np.ndarray, noise_rms: float) -> dict[str, Any]:
    """Per-impact features: f0, spectralCentroid, tau from a 40 ms window."""
    frame_len = int(0.040 * sr)
    n_fft = 8192

    window = samples[onset:onset + frame_len]
    if len(window) < frame_len:
        window = np.pad(window, (0, frame_len - len(window)))

    # Hann, zero-pad, FFT, subtract noise spectrum
    windowed = window * np.hanning(frame_len)
    padded = np.zeros(n_fft)
    padded[:frame_len] = windowed
    mag = np.abs(np.fft.rfft(padded))

    # Trim noise_spectrum to match mag size
    ns = noise_spectrum[:len(mag)] if len(noise_spectrum) >= len(mag) else np.pad(noise_spectrum, (0, len(mag) - len(noise_spectrum)))
    mag = np.maximum(mag - ns, 0)

    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    # f0 = frequency of max magnitude in 80–3000 Hz
    mask = (freqs >= 80) & (freqs <= 3000)
    if not np.any(mask) or np.max(mag[mask]) == 0:
        f0 = 0.0
        centroid = 0.0
    else:
        masked_mag = mag[mask]
        masked_freqs = freqs[mask]
        f0 = float(masked_freqs[np.argmax(masked_mag)])

        # Spectral centroid = magnitude-weighted mean frequency in 80–3000 Hz
        total_mag = np.sum(masked_mag)
        if total_mag > 0:
            centroid = float(np.sum(masked_freqs * masked_mag) / total_mag)
        else:
            centroid = 0.0

    # Tau: Hilbert envelope, fit exponential decay
    analytic = hilbert(window)
    envelope = np.abs(analytic)
    peak_idx = np.argmax(envelope)

    tail = envelope[peak_idx:]
    valid = tail > 2 * noise_rms
    valid_tail = tail[valid]

    if len(valid_tail) >= 2:
        t = np.arange(len(valid_tail)) / sr
        ln_env = np.log(np.maximum(valid_tail, 1e-20))
        # Fit ln(envelope) = a - t/tau by least squares
        A = np.vstack([np.ones_like(t), -t]).T
        result = np.linalg.lstsq(A, ln_env, rcond=None)
        coeffs = result[0]
        if coeffs[1] != 0:
            tau_ms = float(1000.0 / coeffs[1])
        else:
            tau_ms = 10.0
        tau_ms = max(0.1, abs(tau_ms))
    else:
        tau_ms = 10.0

    return {"f0_hz": f0, "spectral_centroid_hz": centroid, "tau_ms": tau_ms}


def _compute_mfcc(samples: np.ndarray, onsets: list[int], sr: int, mode: str) -> list[float]:
    """MFCC: librosa.feature.mfcc over concatenated, z-score-normalized impact windows."""
    import librosa  # lazy import to keep startup fast

    frame_len = int(0.040 * sr)

    if mode == "TAP":
        segments = []
        for onset in onsets:
            window = samples[onset:onset + frame_len]
            if len(window) < frame_len:
                window = np.pad(window, (0, frame_len - len(window)))
            # z-score normalize each window individually
            mean = np.mean(window)
            std = np.std(window)
            if std > 0:
                window = (window - mean) / std
            segments.append(window)
        concat = np.concatenate(segments)
    else:
        # CHIRP: analysis segment 1.5–3.0 s
        start = int(1.5 * sr)
        end = int(3.0 * sr)
        segment = samples[start:end]
        mean = np.mean(segment)
        std = np.std(segment)
        if std > 0:
            segment = (segment - mean) / std
        concat = segment

    mfcc_result = librosa.feature.mfcc(y=concat.astype(np.float32), sr=sr, n_mfcc=13, n_fft=1024, hop_length=256)
    mfcc_mean = np.mean(mfcc_result, axis=1).tolist()
    return mfcc_mean


def process_tap(samples: np.ndarray, sr: int) -> dict[str, Any]:
    """Full TAP mode processing pipeline. Returns scan features dict."""
    filtered = _bandpass(samples, sr)
    noise_rms, noise_spectrum = _noise_floor(filtered, sr)

    onsets = _detect_impacts(filtered, sr, noise_rms)
    if len(onsets) < 3:
        raise ApiError(422, "IMPACTS_NOT_DETECTED",
                       "Could not detect 3 tap impacts in the recording",
                       {"impactsFound": len(onsets), "required": 3})

    onsets = onsets[:3]
    features = [_impact_features(filtered, o, sr, noise_spectrum, noise_rms) for o in onsets]

    tap_f0_values = [f["f0_hz"] for f in features]
    f0_hz = float(np.mean(tap_f0_values))
    centroid = float(np.mean([f["spectral_centroid_hz"] for f in features]))
    tau_ms = float(np.mean([f["tau_ms"] for f in features]))

    # Variation check
    std_f0 = float(np.std(tap_f0_values, ddof=0))  # population std
    variation_pct = (std_f0 / f0_hz * 100) if f0_hz > 0 else 0.0

    if variation_pct > 12:
        raise ApiError(422, "SCAN_REJECTED_TAP_VARIATION",
                       "Taps were inconsistent. Tap the same spot on the fruit's equator again.",
                       {"tapF0ValuesHz": [round(v, 1) for v in tap_f0_values],
                        "tapVariationPct": round(variation_pct, 1),
                        "maxAllowedPct": 12})

    mfcc_mean = _compute_mfcc(filtered, onsets, sr, "TAP")

    return {
        "f0_hz": f0_hz,
        "tap_f0_values_hz": tap_f0_values,
        "tap_variation_pct": variation_pct,
        "spectral_centroid_hz": centroid,
        "tau_ms": tau_ms,
        "mfcc_mean": mfcc_mean,
    }


def process_chirp(samples: np.ndarray, sr: int) -> dict[str, Any]:
    """Full CHIRP mode processing pipeline. Returns scan features dict."""
    filtered = _bandpass(samples, sr)
    noise_rms, noise_spectrum = _noise_floor(filtered, sr)

    # Analyse 1.5–3.0 s
    start_sample = int(1.5 * sr)
    end_sample = int(3.0 * sr)
    segment = filtered[start_sample:end_sample]

    n_fft = 8192
    windowed = segment * np.hanning(len(segment))
    padded = np.zeros(n_fft)
    padded[:len(windowed)] = windowed
    mag = np.abs(np.fft.rfft(padded))

    ns = noise_spectrum[:len(mag)] if len(noise_spectrum) >= len(mag) else np.pad(noise_spectrum, (0, len(mag) - len(noise_spectrum)))
    mag = np.maximum(mag - ns, 0)

    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    mask = (freqs >= 100) & (freqs <= 2500)

    if not np.any(mask):
        raise ApiError(422, "IMPACTS_NOT_DETECTED",
                       "No resonance peak detected in chirp response",
                       {"impactsFound": 0, "required": 1})

    masked_mag = mag[mask]
    masked_freqs = freqs[mask]

    noise_median = float(np.median(masked_mag))
    peak_val = float(np.max(masked_mag))

    if peak_val < 3 * noise_median:
        raise ApiError(422, "IMPACTS_NOT_DETECTED",
                       "No resonance peak above noise floor in chirp response",
                       {"impactsFound": 0, "required": 1})

    f0_hz = float(masked_freqs[np.argmax(masked_mag)])

    # Spectral centroid
    total_mag = np.sum(masked_mag)
    centroid = float(np.sum(masked_freqs * masked_mag) / total_mag) if total_mag > 0 else f0_hz

    # tau from -3 dB bandwidth
    peak_idx_in_mask = np.argmax(masked_mag)
    half_power = peak_val / np.sqrt(2)

    # Find bandwidth
    left = peak_idx_in_mask
    while left > 0 and masked_mag[left] > half_power:
        left -= 1
    right = peak_idx_in_mask
    while right < len(masked_mag) - 1 and masked_mag[right] > half_power:
        right += 1

    delta_f = masked_freqs[right] - masked_freqs[left]
    if delta_f > 0:
        tau_ms = 1000.0 / (np.pi * delta_f)
    else:
        tau_ms = 10.0

    mfcc_mean = _compute_mfcc(filtered, [], sr, "CHIRP")

    return {
        "f0_hz": f0_hz,
        "tap_f0_values_hz": [f0_hz],
        "tap_variation_pct": None,
        "spectral_centroid_hz": centroid,
        "tau_ms": tau_ms,
        "mfcc_mean": mfcc_mean,
    }
