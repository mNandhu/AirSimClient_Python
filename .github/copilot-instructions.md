# Copilot instructions for this repo

Mission: Build an HRL (Hierarchical Reinforcement Learning) training platform for a self‑driving car using multiple AirSim instances (local/cluster). The current CLI and example scripts exist to explore the AirSim API and collect quick data; they’re supporting tools, not the end goal.

## Direction of travel (HRL-first)

- Target architecture (planned):
  - Orchestrator: manages N AirSim environments (host:port per instance), schedules episodes, resets, and seeds.
  - Env worker API: thin wrapper around AirSim RPC for step/reset/observe/act, supporting car control and sensors (cameras, LiDAR).
  - HRL agent: high-level manager (options/skills) + low-level controllers; shared replay buffers and logging.
  - Storage: data under `data/` (raw), experiment outputs in `runs/` (checkpoints, metrics, artifacts).
- Conventions: prefer environment-driven config (`.env`, JSON/YAML later), deterministic runs via seeds, and non-blocking RPC usage.

## What exists today (useful now)

- Entry point: `airsim-cli` → `cli:main` (Typer). Requires a running AirSim sim.
- Layout: `cli.py`, examples in `examples/`, helper scripts in `scripts/`, repo‑root `.env` and `settings.json`, outputs in `data/` and `runs/`.
- Key deps: `airsim`, `typer`/`rich`, `python-dotenv`, `ultralytics` (YOLO), `open3d`.
- Examples are discovered by file name and run in‑process (`runpy`), with `sys.argv` reset → examples should not parse CLI args; use constants/env. Descriptions come from docstrings/top comments (see `examples/hello_car.py`).
- `yield_control.py` toggles `enableApiControl(False)` when `--yield-control` is passed to `airsim-cli run`.

## Integration details you’ll need

- `.env` auto-loaded with fallbacks: `CAR_NAME=Car1`, `AIRSIM_HOST=127.0.0.1`, `AIRSIM_PORT=41451`.
- `settings.json` edits via CLI: `SimMode`, and `Vehicles.<Key>.Sensors.Lidar360.{Enabled,PointsPerSecond}`.
- Cameras may be named (`Front/Right/Back/Left`) or numeric strings (`"0"`, `"1"`). Always `confirmConnection()`; if you take API control, release it afterward.
- Tornado SyntaxWarning from AirSim is suppressed in `cli.py`.

## Data flows and quick tools

- Images: `scripts/recognize_camera_yolo.py` reads multiple cameras, runs Ultralytics YOLO (weights like `yolo11s.pt` in repo root), writes annotated JPGs to `runs/recognize/`.
- LiDAR: `scripts/recognize_lidar.py` grabs one scan from `Lidar360`, preprocesses, DBSCAN clusters via Open3D, optional `runs/lidar/clusters_colored.pcd` and visualization.

## Working effectively here

- Use `uv sync` to prepare the env; optional `uv pip install -e .` to add `airsim-cli` to PATH.
- Typical commands (PowerShell): list → `airsim-cli examples`; run → `airsim-cli run hello_car --yield-control`; config → `airsim-cli settings --show` or enable LiDAR via `--enable-lidar --lidar-pps 200000`.
- When you start implementing HRL orchestration, introduce a minimal env wrapper and orchestrator module alongside (do not break existing CLI). Keep configs in `.env`/JSON first; add YAML only if needed.
