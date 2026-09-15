import hashlib
import sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "research-code"))
from sampling import fixed_rate_plan


def decode(row, cfg):
    s = cfg["sampling"]
    plan = fixed_rate_plan(row["frame_count"], row["fps"], s["target_fps"], s["window_sec"])
    cap = cv2.VideoCapture(row["path"], cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    frames, pts, decoded_indices = [], [], []
    try:
        if not cap.isOpened():
            raise RuntimeError("cannot open video")
        for index in plan.indices:
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, index):
                raise RuntimeError("seek failed")
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"decode failure at {index}")
            pts.append(float(cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000)
            decoded_indices.append(int(round(cap.get(cv2.CAP_PROP_POS_FRAMES))) - 1)
            h, w = frame.shape[:2]
            side = min(h, w)
            cropped = frame[(h-side)//2:(h-side)//2+side, (w-side)//2:(w-side)//2+side]
            frames.append(cv2.resize(cropped, (s["size"], s["size"]), interpolation=cv2.INTER_AREA))
    finally:
        cap.release()
    if tuple(decoded_indices) != plan.indices:
        raise RuntimeError("decoder returned unexpected indices")
    if not np.isfinite(pts).all() or not np.all(np.diff(pts) > 0):
        raise RuntimeError("missing or non-increasing decoded timestamps; no silent CFR fallback")
    bgr = np.stack(frames)
    gray = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in bgr])
    q = cfg["quality"]
    black = np.mean((gray.mean((1,2)) < q["black_gray_mean_below"]) & (gray.std((1,2)) < q["black_gray_std_below"]))
    duplicate_content = len(frames) - len({hashlib.sha256(f.tobytes()).hexdigest() for f in bgr})
    info = {"indices": list(plan.indices), "pts": pts, "dt": np.diff(pts).tolist(), "black_frame_fraction": float(black), "duplicate_resized_frames": duplicate_content}
    return bgr, info


def warp_previous(previous, backward_flow):
    h, w = previous.shape[:2]
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    mx, my = xx + backward_flow[..., 0], yy + backward_flow[..., 1]
    valid = (mx >= 0) & (mx <= w-1) & (my >= 0) & (my <= h-1)
    warped = cv2.remap(previous, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return warped, valid


def represent(bgr, cfg):
    fcfg = cfg["flow"]
    rgb = bgr[..., ::-1].copy().astype(np.float32) / 255
    gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in bgr]
    raw, aligned, coverage = [], [], []
    for t in range(1, len(bgr)):
        flow = cv2.calcOpticalFlowFarneback(gray[t], gray[t-1], None, fcfg["pyr_scale"], fcfg["levels"], fcfg["winsize"], fcfg["iterations"], fcfg["poly_n"], fcfg["poly_sigma"], fcfg["flags"])
        warped, valid = warp_previous(rgb[t-1], flow)
        mask = valid[..., None]
        raw.append((rgb[t] - rgb[t-1]) * mask)
        aligned.append((rgb[t] - warped) * mask)
        coverage.append(float(valid.mean()))
    result = {"frame_mean": (rgb - .5).transpose(0,3,1,2),
              "raw_temporal": np.stack(raw).transpose(0,3,1,2),
              "aligned_temporal": np.stack(aligned).transpose(0,3,1,2)}
    if not all(np.isfinite(x).all() for x in result.values()):
        raise RuntimeError("nonfinite representation")
    return result, coverage


def corrupt(bgr, condition, cfg, sid):
    if condition == "clean":
        return bgr.copy()
    params = cfg["conditions"][condition]
    if condition == "jpeg70":
        output = []
        for frame in bgr:
            ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, params["quality"]])
            if not ok:
                raise RuntimeError("JPEG encode failed")
            output.append(cv2.imdecode(encoded, cv2.IMREAD_COLOR))
        return np.stack(output)
    if condition == "gaussian5":
        seed = params["seed"] ^ int(hashlib.sha256(sid.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        return np.clip(bgr.astype(float) + rng.normal(0, params["sigma_255"], bgr.shape), 0, 255).round().astype(np.uint8)
    raise ValueError(condition)
