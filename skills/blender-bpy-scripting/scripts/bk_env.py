"""Measure this machine's render environment and emit a baseline fingerprint.

Run it on any machine to find out what that machine's numbers *mean* relative
to the machine the references were measured on:

    blender -b --factory-startup -noaudio -P scripts/bk_env.py -- [--json] [--bench]

`--bench` additionally times a tiny fixed render so you can compute a scale
factor instead of guessing. Everything else is cheap metadata.

Measured on the reference machine: see references/17-environment-baseline.md
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

import bpy  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))


def _sh(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def _cpu():
    info = {
        "model": _sh("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-"),
        "logical_cores": os.cpu_count(),
        "physical_cores": None,
        "l3_cache_mb": None,
        "governor": None,
    }
    info["model"] = info["model"] or platform.processor() or "unknown"
    # lscpu is localised on this box (ja_JP), so the English keys do not match.
    # lscpu -p emits machine-readable field names in English regardless.
    cores_raw = _sh("lscpu -p=Core,Socket | grep -v '^#'")
    if cores_raw:
        pairs = set()
        for line in cores_raw.splitlines():
            parts = line.split(",")
            if len(parts) >= 2:
                pairs.add((parts[0], parts[1]))
        if pairs:
            info["physical_cores"] = len(pairs)
    if info["physical_cores"] is None:
        cores = _sh("lscpu | awk -F: '/^Core\\(s\\) per socket/{print $2}'").strip()
        sockets = _sh("lscpu | awk -F: '/^Socket\\(s\\)/{print $2}'").strip()
        try:
            info["physical_cores"] = int(cores) * int(sockets or 1)
        except Exception:
            info["physical_cores"] = None
    l3 = _sh("lscpu | grep -m1 -iE 'l3 cache|L3 キャ'")
    m = re.search(r"([\d.]+)\s*(M|G|K)iB", l3 or "")
    if m:
        v = float(m.group(1))
        unit = m.group(2)
        info["l3_cache_mb"] = round(v / 1024 if unit in ("G", "K") else v, 1)
    gov = _sh("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if gov:
        info["governor"] = gov
    return info


def _memory_gb():
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1048576, 1)
    except Exception:
        return None
    return None


def _load():
    try:
        return round(os.getloadavg()[0], 2)
    except Exception:
        return None


def _disk_read_gbs(mb=256):
    tmp = os.path.join("/tmp", f".bk_diskbench_{os.getpid()}")
    try:
        subprocess.run(f"dd if=/dev/zero of={tmp} bs=1M count={mb} conv=fdatasync",
                       shell=True, capture_output=True, timeout=120)
        out = _sh(f"dd if={tmp} of=/dev/null bs=1M 2>&1 | tail -1")
        os.remove(tmp)
        m = re.search(r"([\d.]+)\s*(G|M)B/s", out)
        if not m:
            return None
        v = float(m.group(1))
        return round(v if m.group(2) == "G" else v / 1024, 2)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return None


def _disk_free_gb(path=None):
    path = path or os.environ.get("TMPDIR") or "/tmp"
    try:
        st = shutil.disk_usage(path)
        return round(st.free / 1e9, 1)
    except Exception:
        return None


def _gpu():
    out = {"backend": None, "compiled": {}, "devices": [], "usable": 0,
           "vendor": None, "total_vram_mb": 0, "free_vram_mb": 0}
    try:
        from bkkit import compat
        rep = compat.gpu_report(probe_host=True)
        out["backend"] = rep.get("backend")
        out["compiled"] = {k: v for k, v in rep.get("compiled", {}).items() if v}
        seen = set()
        for d in rep.get("devices", []):
            if d["backend"] != out["backend"]:
                continue
            h = d.get("host") or {}
            key = d.get("bus_id")
            if key in seen:
                continue
            seen.add(key)
            out["devices"].append({"name": d["name"], "bus": key,
                                   "free_mb": h.get("free_mb"),
                                   "total_mb": h.get("total_mb")})
        out["usable"] = len(rep.get("usable", []))
        names = " ".join(x["name"] for x in out["devices"]).upper()
        out["vendor"] = "NVIDIA" if "NVIDIA" in names else ("AMD" if "AMD" in names else None)
        out["total_vram_mb"] = sum(x["total_mb"] or 0 for x in out["devices"])
        out["free_vram_mb"] = sum(x["free_mb"] or 0 for x in out["devices"])
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def collect():
    return {
        "blender": bpy.app.version_string,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": _cpu(),
        "ram_gb": _memory_gb(),
        "load1": _load(),
        "disk_read_gbs": _disk_read_gbs(),
        "disk_free_gb": _disk_free_gb(),
        "gpu": _gpu(),
    }


#: Warm-time benchmark recorded on the reference machine (see
#: references/17-environment-baseline.md). If a machine's own bench is far
#: from this, the environment -- not the script -- changed; re-baseline before
#: trusting any per-second number quoted in the references.
REFERENCE_BENCH_WARM_S = 0.68
REFERENCE_GPU = "NVIDIA GeForce RTX 4070"


def bench(freeze=64, res=320):
    """Time one tiny fixed render. Use this to scale to other machines."""
    sys.path.insert(0, os.path.join(HERE, "scripts"))
    from bkkit import compat
    addon_ok = compat.enable_cycles()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    compat.set_engine(sc, "CYCLES")
    ok = False
    info = {}
    try:
        ok, info = compat.enable_gpu(sc)
    except Exception:
        ok = False
    sc.cycles.device = "GPU" if ok else "CPU"
    sc.cycles.samples = freeze
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.filepath = "/tmp/.bk_bench.png"
    bpy.ops.mesh.primitive_monkey_add()
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 5))
    bpy.context.object.data.energy = 5
    bpy.ops.object.camera_add(location=(0, -5, 1.5), rotation=(1.57, 0, 0))
    sc.camera = bpy.context.object
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    cold = time.time() - t0
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    warm = time.time() - t0
    try:
        os.remove("/tmp/.bk_bench.png")
    except Exception:
        pass
    return {"cold_s": round(cold, 2), "warm_s": round(warm, 2),
            "device": sc.cycles.device,
            "gpu_count": info.get("num_gpu_devices", 0),
            "backend": info.get("chosen")}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    data = collect()
    if "--bench" in argv:
        data["bench"] = bench()
    if "--json" in argv or not argv:
        print(json.dumps(data, indent=2))
        return 0
    print(f"Blender      : {data['blender']}  (Python {data['python']})")
    print(f"Platform     : {data['platform']}")
    c = data["cpu"]
    print(f"CPU          : {c['model']}")
    print(f"               {c['logical_cores']} logical / {c['physical_cores']} physical, "
          f"L3={c['l3_cache_mb']} MB, governor={c['governor']}")
    print(f"RAM          : {data['ram_gb']} GB    load(1m): {data['load1']}")
    print(f"Disk         : read {data['disk_read_gbs']} GB/s, free {data['disk_free_gb']} GB")
    g = data["gpu"]
    print(f"GPU          : backend={g['backend']} vendor={g['vendor']} "
          f"usable={g['usable']} vram_free={g['free_vram_mb']}/{g['total_vram_mb']} MB")
    for d in g["devices"]:
        print(f"               {d['name']:<28} bus={d['bus']} free={d['free_mb']} MB")
    if "bench" in data:
        b = data["bench"]
        print(f"Bench        : cold {b['cold_s']}s  warm {b['warm_s']}s  "
              f"device={b['device']} gpus={b['gpu_count']}")
        ratio = b["warm_s"] / REFERENCE_BENCH_WARM_S if REFERENCE_BENCH_WARM_S else 0
        print()
        print(f"기준값        : warm {REFERENCE_BENCH_WARM_S}s "
              f"({REFERENCE_GPU})  → 이 머신은 기준의 {ratio:.2f}배")
        if ratio > 1.8 or ratio < 0.55:
            print()
            print("⚠ 기준값에서 크게 벗어났다. 흔한 원인은:")
            print("  · 선택된 GPU 가 바뀌었거나 다른 작업이 GPU 를 잡고 있다")
            print("  · CPU 부하 (load 참고), 클럭 조정, 노트북 저전력 모드")
            print("  · 다른 드라이버/Blender 버전")
            print("  references/*.md 의 초 단위 수치를 그대로 믿지 말고,")
            print("  먼저 위 원인을 제외한 뒤 배율로 환산하라.")
        for d in g["devices"]:
            print(f"               {d['name']:<28} free={d['free_mb']} MB")
        print()
        print("이 bench 값과 references/17-environment-baseline.md 의 기준값을")
        print("비교하면 이 머신의 상대 성능을 추정할 수 있다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
