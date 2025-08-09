# AirSim Client Python CLI

This project provides a Typer-based CLI to run AirSim car examples, tweak `settings.json`, and yield control back to keyboard.

## Quick start

1. Install dependencies (managed by `uv`):

   - Sync the environment

   ```powershell
   uv sync
   ```

2. Ensure the AirSim simulator is running.

3. List available examples:

   ```powershell
   uv run airsim-cli examples
   ```

4. Run an example (e.g., `hello_car`) and yield control after:

   ```powershell
   uv run airsim-cli run hello_car --yield-control
   ```

5. View or update `settings.json`:

   - Show current settings

   ```powershell
   uv run airsim-cli settings --show
   ```

   - Enable lidar and change points per second, then save

   ```powershell
   uv run airsim-cli settings --vehicle Car1 --enable-lidar --lidar-pps 200000 --save
   ```

## .env configuration

Create a `.env` file to configure defaults:

```
CAR_NAME=Car1
AIRSIM_HOST=127.0.0.1
AIRSIM_PORT=41451
```

These are loaded automatically by the CLI.

## Dependencies management

Use `uv` to manage dependencies:

- Add a package:

  ```powershell
  uv add <package>
  ```

- Remove a package:

  ```powershell
  uv remove <package>
  ```

## Tools

- `airsim-cli examples`: List example scripts in `examples/` with short descriptions.
- `airsim-cli describe <name>`: Show detailed description and the file path for an example.
- `airsim-cli run <name> [--yield-control] [--car-name <Car>]`: Run an example by stem name and optionally yield control.
- `airsim-cli settings [--show] [--sim-mode <Mode>] [--vehicle <Key>] [--enable-lidar|--disable-lidar] [--lidar-pps <int>] [--save]`: Inspect and modify `settings.json`.

## Data collection

- Capture images from a camera and save PNGs:

  ```powershell
  uv run airsim-cli capture-images --camera Front --count 20 --interval 0.25 --out-dir data/images
  ```

- Dump a single lidar scan to CSV:

  ```powershell
  uv run airsim-cli lidar-dump --sensor-name Lidar360 --out-file data/lidar/points.csv
  ```
