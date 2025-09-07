# HRL Self‑Driving Car on AirSim

Primary goal: build a Hierarchical Reinforcement Learning (HRL) training platform for an autonomous car on top of multiple AirSim instances (local or cluster). The current CLI and example scripts exist to explore the AirSim API and collect quick data—they are supporting tools while we design the HRL orchestrator and agent.

## Status

- Today: Typer-based CLI (`airsim-cli`) to run examples, tweak `settings.json`, and collect images/LiDAR.
- Next: introduce a minimal environment wrapper and an orchestrator to manage N AirSim instances (host:port per instance), then layer the HRL agent (high-level options + low-level controllers).

## Planned architecture (HRL‑first)

- Orchestrator: manages instance lifecycle (connect/reset/seed), schedules episodes across multiple AirSim servers.
- Env worker API: thin wrapper over AirSim RPC for step/reset/observe/act; supports car controls and sensors (cameras, LiDAR).
- HRL agent: high‑level manager (options/skills) coordinating low‑level controllers; shared replay buffers/logging.
- Storage & outputs: raw under `data/`, experiment outputs/artifacts under `runs/`.
- Conventions: environment-driven config via `.env` and JSON first; deterministic seeds; avoid blocking RPCs when possible.

The CLI documented below remains as a quick, reliable way to interact with the simulator and gather sample data while the HRL stack is built.

## AirSim Client CLI (supporting tool)

A simple CLI to run examples and manage settings.

### Quick start

1. Install dependencies (managed by `uv`):

   - Sync the environment

   ```powershell
   uv sync
   ```

2. Ensure the AirSim simulator is running.

3. List available examples:

   ```powershell
   airsim-cli examples
   ```

4. Run an example (e.g., `hello_car`) and yield control after:

   ```powershell
   airsim-cli run hello_car --yield-control
   ```

5. View or update `settings.json`:

   - Show current settings

   ```powershell
   airsim-cli settings --show
   ```

   - Enable lidar and change points per second, then save

   ```powershell
   airsim-cli settings --vehicle Car1 --enable-lidar --lidar-pps 200000 --save
   ```

#### Install the CLI into your active environment

If you want to use `airsim-cli` without `uv run`, install it to your active Python environment:

```powershell
uv pip install -e .
```

Then run it directly:

```powershell
airsim-cli --help
```

### .env configuration

Create a `.env` file to configure defaults:

```text
CAR_NAME=Car1
AIRSIM_HOST=127.0.0.1
AIRSIM_PORT=41451
```

These are loaded automatically by the CLI.

### Dependencies management

Use `uv` to manage dependencies:

- Add a package:

  ```powershell
  uv add <package>
  ```

- Remove a package:

  ```powershell
  uv remove <package>
  ```

### CLI commands

- `airsim-cli examples`: List example scripts in `examples/` with short descriptions.
- `airsim-cli describe <name>`: Show detailed description and the file path for an example.
- `airsim-cli run <name> [--yield-control] [--car-name <Car>]`: Run an example by stem name and optionally yield control.
- `airsim-cli settings [--show] [--sim-mode <Mode>] [--vehicle <Key>] [--enable-lidar|--disable-lidar] [--lidar-pps <int>] [--save]`: Inspect and modify `settings.json`.

### Data collection

- Capture images from a camera and save PNGs:

  ```powershell
  airsim-cli capture-images --camera Front --count 20 --interval 0.25 --out-dir data/images
  ```

- Dump a single lidar scan to CSV:

  ```powershell
  airsim-cli lidar-dump --sensor-name Lidar360 --out-file data/lidar/points.csv
  ```

## Roadmap

1. Minimal AirSim env wrapper: `reset/step/observe/act` for car control + sensors; seed-able and environment-driven config.
2. Orchestrator: manage N instances (host:port per instance), schedule episodes, collect rollouts concurrently.
3. HRL skeleton: options/skills interface (high-level) with low-level controllers; shared replay buffers; logging/metrics under `runs/`.
4. Training loop: integrate with Stable-Baselines3 for baselines; implement HRL-specific training and evaluation flows.
5. Scaling: multi-process and (eventually) multi-node support for running many AirSim instances.
6. Testing & reliability: smoke tests for env wrapper/orchestrator; determinism checks via seeds.
