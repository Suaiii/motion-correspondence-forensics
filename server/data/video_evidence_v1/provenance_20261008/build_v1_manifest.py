from __future__ import annotations

import concurrent.futures
import hashlib
import json
import pathlib
import subprocess
import time


OUT = pathlib.Path(r"E:\aNB\TECH\脉冲神经网络\research-runs\VIDEO_EVIDENCE_V1_20261004")
AAG = pathlib.Path(r"E:\AAGenvid")
V02 = AAG / "Dataset" / "RoboVid-SM" / "v02"
AEGIS = AAG / "Dataset" / "AEGIS_HardTest" / "test_data"
FFPROBE = pathlib.Path(r"E:\anaconda\Library\bin\ffprobe.exe")
P0 = pathlib.Path(r"E:\aNB\TECH\脉冲神经网络\research-runs\P0_robovid_sm_test_audit_20261004\manifest.jsonl")
RANDOM_MANIFEST = AAG / "Dataset" / "RoboVid-SM" / "manifests" / "real_manifest_v02_random.jsonl"
SPLIT_MANIFEST = AAG / "Dataset" / "RoboVid-SM" / "splits" / "split_manifest.csv"
AEGIS_README = AAG / "external_datasets" / "AEGIS" / "README.md"
AEGIS_MAPPING = AAG / "external_datasets" / "AEGIS" / "data" / "mapping_test_data.csv"
AEGIS_TAR = AAG / "external_datasets" / "AEGIS" / "data" / "hard_test_set_video.tar"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def random_pair_map() -> dict[tuple[str, str], dict]:
    out = {}
    for no, line in enumerate(RANDOM_MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        for key, label in (("real_file", 0), ("fake_file", 1)):
            stem = pathlib.Path(rec[key]).stem
            out[(stem, str(label))] = {
                "pair_record": f"random_pair_{no:04d}",
                "vript_clip_id": rec.get("vript_clip_id"),
                "query": rec.get("query"),
                "semantic_score": rec.get("semantic_score"),
                "content_pairing": rec.get("reason", "random_pair"),
            }
    return out


def probe(path: pathlib.Path) -> dict:
    cmd = [str(FFPROBE), "-v", "error", "-select_streams", "v:0",
           "-show_entries",
           "stream=index,codec_name,r_frame_rate,avg_frame_rate,time_base,nb_frames,duration,width,height:"
           "frame=pts,pts_time,best_effort_timestamp_time,pkt_duration_time",
           "-of", "json", str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f"ffprobe_exit_{p.returncode}")
    obj = json.loads(p.stdout)
    streams = obj.get("streams", [])
    if not streams:
        raise RuntimeError("no_video_stream")
    s = streams[0]
    frames = obj.get("frames", [])
    pts = [x.get("pts") for x in frames]
    ints = [x for x in pts if isinstance(x, int)]
    complete = len(pts) == len(frames) and len(ints) == len(pts)
    mono = all(a <= b for a, b in zip(ints, ints[1:])) if complete else False
    pts_bytes = json.dumps(pts, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "codec_name": s.get("codec_name"),
        "r_frame_rate": s.get("r_frame_rate"),
        "avg_frame_rate": s.get("avg_frame_rate"),
        "time_base": s.get("time_base"),
        "nb_frames_stream": s.get("nb_frames"),
        "duration_stream": s.get("duration"),
        "width": s.get("width"),
        "height": s.get("height"),
        "frame_count_probed": len(frames),
        "pts": pts,
        "pts_time": [x.get("pts_time") for x in frames],
        "best_effort_timestamp_time": [x.get("best_effort_timestamp_time") for x in frames],
        "pkt_duration_time": [x.get("pkt_duration_time") for x in frames],
        "native_pts_complete": complete,
        "native_pts_monotonic": mono,
        "native_pts_sequence_sha256": hashlib.sha256(pts_bytes).hexdigest(),
    }


SORA_STEMS = {p.stem for p in (AAG / "Dataset" / "OpenAI_Sora").glob("*.mp4")}


def fake_generator(stem: str) -> tuple[str, str]:
    low = stem.lower()
    if low.startswith("opensora"):
        return "OpenSora", "OpenSora"
    if low.startswith("t2vz"):
        return "T2V-Zero", "T2V-Zero"
    if stem in SORA_STEMS:
        return "OpenAI-Sora", "OpenAI-Sora"
    return "unknown_fake", "unknown_fake"


def add_aag_jobs() -> list[dict]:
    pair_map = random_pair_map()
    jobs = []
    roots = [("clean", V02 / "splits"), ("osn", V02 / "splits_osn"),
             ("wechat", V02 / "splits_osn_wechat"), ("whatsapp", V02 / "splits_osn_whatsapp")]
    for variant, root in roots:
        for split in ("train", "val", "test"):
            for label, label_name in ((0, "real"), (1, "fake")):
                d = root / split / label_name
                if not d.exists():
                    continue
                for p in sorted(d.glob("*.mp4")):
                    stem = p.stem
                    gen, family = ("real", "real_vript") if label == 0 else fake_generator(stem)
                    pair = pair_map.get((stem, str(label)), {})
                    jobs.append({
                        "package": "AAGenvid_RoboVidSM_v02",
                        "sample_id": stem,
                        "split": split,
                        "label_fake": label,
                        "label": label_name,
                        "variant": variant,
                        "path": str(p),
                        "relative_path": str(p.relative_to(AAG)).replace("\\", "/"),
                        "source": "Vript" if label == 0 else "RoboVidSM_generated",
                        "generator": gen,
                        "generator_family": family,
                        "generation_mode": "unknown",
                        "pair_record": pair.get("pair_record"),
                        "vript_clip_id": pair.get("vript_clip_id"),
                        "query": pair.get("query"),
                        "semantic_score": pair.get("semantic_score"),
                        "content_pairing": pair.get("content_pairing", "unknown"),
                        "ancestor_status": "not_verified",
                        "license_status": "not_verified",
                        "dataset_revision": "RoboVid-SM-v02",
                        "role": "benchmark_candidate",
                        "scope": "v1_propagation_benchmark",
                    })
    return jobs


def add_aegis_jobs() -> list[dict]:
    jobs = []
    for p in sorted(AEGIS.rglob("*.mp4")):
        rel = p.relative_to(AEGIS)
        parts = [x.lower() for x in rel.parts]
        if "ai_gen" in parts:
            label, label_name = 1, "fake"
            generator = rel.parts[1] if len(rel.parts) > 1 else "unknown_ai_gen"
            family = generator
            source = "AEGIS_HardTest"
        else:
            label, label_name = 0, "real"
            generator = "real_" + (rel.parts[1] if len(rel.parts) > 1 else "unknown")
            family = generator
            source = "AEGIS_HardTest"
        jobs.append({
            "package": "AEGIS_HardTest",
            "sample_id": "AEGIS/" + str(rel.with_suffix("")).replace("\\", "/"),
            "split": "hard_test",
            "label_fake": label,
            "label": label_name,
            "variant": "clean",
            "path": str(p),
            "relative_path": str(p.relative_to(AAG)).replace("\\", "/"),
            "source": source,
            "generator": generator,
            "generator_family": family,
            "generation_mode": "unknown",
            "pair_record": None,
            "vript_clip_id": None,
            "query": None,
            "semantic_score": None,
            "content_pairing": "unknown",
            "ancestor_status": "not_verified",
            "license_status": "custom_academic_use",
            "dataset_revision": "AEGIS_HardTest",
            "role": "external_holdout",
            "scope": "v1_external_holdout",
        })
    return jobs


def audit(jobs: list[dict]) -> list[dict]:
    def one(row: dict) -> dict:
        try:
            p = pathlib.Path(row["path"])
            row["file_size"] = p.stat().st_size
            row["sha256"] = sha256(p)
            row["ffprobe"] = probe(p)
            row["status"] = "ok"
        except Exception as exc:
            row["status"] = "error"
            row["error"] = repr(exc)
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(one, jobs))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    jobs = add_aag_jobs() + add_aegis_jobs()
    rows = audit(jobs)
    manifest = OUT / "v1_manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    errors = [r for r in rows if r["status"] != "ok"]
    incomplete = [r for r in rows if r["status"] == "ok" and not r["ffprobe"]["native_pts_complete"]]
    summary = {
        "version": "video_evidence_v1",
        "created_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_sec": time.time() - started,
        "row_count": len(rows),
        "ok_count": sum(r["status"] == "ok" for r in rows),
        "error_count": len(errors),
        "native_pts_incomplete_count": len(incomplete),
        "packages": {
            "AAGenvid_RoboVidSM_v02": sum(r["package"] == "AAGenvid_RoboVidSM_v02" for r in rows),
            "AEGIS_HardTest": sum(r["package"] == "AEGIS_HardTest" for r in rows),
        },
        "scope": "stable data inventory and propagation benchmark candidate; not formal mechanism acceptance",
        "formal_gate": False,
        "manifest_sha256": sha256(manifest),
        "inputs": {
            "random_manifest_sha256": sha256(RANDOM_MANIFEST),
            "split_manifest_sha256": sha256(SPLIT_MANIFEST),
            "aegis_readme_sha256": sha256(AEGIS_README),
            "aegis_mapping_sha256": sha256(AEGIS_MAPPING),
            "aegis_tar_sha256": sha256(AEGIS_TAR),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
