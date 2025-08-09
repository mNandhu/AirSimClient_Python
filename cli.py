from __future__ import annotations

import json
import os
import runpy
from pathlib import Path
import time
from typing import Optional
import ast

import typer
from rich import print as rprint
from rich.table import Table
from dotenv import load_dotenv
import airsim


APP_NAME = "airsim-cli"
app = typer.Typer(
    help="AirSim Car Simulation CLI: run examples, tweak settings, and control API."
)


# Defaults and paths
ROOT = Path(__file__).parent
EXAMPLES_DIR = ROOT / "examples"
SETTINGS_FILE = ROOT / "settings.json"


def load_env() -> None:
    """Load .env if present and expose defaults."""
    load_dotenv()
    # Provide convenient defaults if not set
    os.environ.setdefault("AIRSIM_HOST", "127.0.0.1")
    os.environ.setdefault("AIRSIM_PORT", "41451")
    os.environ.setdefault("CAR_NAME", "Car1")


def list_example_scripts() -> list[Path]:
    if not EXAMPLES_DIR.exists():
        return []
    return sorted(p for p in EXAMPLES_DIR.glob("*.py") if p.name != "setup_path.py")


def run_script(path: Path, env_overrides: dict[str, str] | None = None) -> int:
    """Run a Python script in-process using runpy, with optional environment overrides."""
    env_overrides = env_overrides or {}
    prev_env = {}
    try:
        for k, v in env_overrides.items():
            prev_env[k] = os.environ.get(k)
            os.environ[k] = str(v)
        runpy.run_path(str(path), run_name="__main__")
        return 0
    except SystemExit as e:
        # allow scripts calling sys.exit to map to exit code
        return int(e.code or 0)
    except Exception as e:  # noqa: BLE001
        rprint(f"[red]Error while running {path.name}: {e}")
        return 1
    finally:
        for k, v in prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def read_settings() -> dict:
    if not SETTINGS_FILE.exists():
        rprint(f"[yellow]settings.json not found at {SETTINGS_FILE}")
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        rprint(f"[red]Failed to parse settings.json: {e}")
        return {}


def write_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _extract_comment_block(lines: list[str]) -> str | None:
    """Extract contiguous top-of-file comment lines as description."""
    desc_lines: list[str] = []
    started = False
    for line in lines:
        s = line.strip()
        if not started and (
            s == ""
            or s.startswith("#!")
            or s.lower().startswith("# -*-")
            or s.lower().startswith("# coding")
        ):
            continue
        if s.startswith("#"):
            started = True
            # strip leading '# ' or '#'
            desc_lines.append(s[1:].lstrip())
        elif started:
            break
        else:
            # first non-comment content encountered
            break
    desc = "\n".join(line for line in desc_lines if line is not None)
    return desc if desc.strip() else None


def extract_example_description(path: Path) -> tuple[str, str]:
    """Return (short, long) descriptions from module docstring or top comments."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ("(unreadable)", "")

    long_desc = ""
    try:
        mod = ast.parse(text)
        doc = ast.get_docstring(mod)
        if doc:
            long_desc = doc.strip()
    except Exception:  # noqa: BLE001
        long_desc = ""

    if not long_desc:
        lines = text.splitlines()[:150]
        comm = _extract_comment_block(lines)
        if comm:
            long_desc = comm.strip()

    long_desc = long_desc or "(no description)"
    # short = first line or first sentence
    first_line = long_desc.splitlines()[0]
    short = first_line.split(". ")[0].strip()
    return (short, long_desc)


@app.command("examples")
def list_examples():
    """List available example scripts with a short description."""
    load_env()
    scripts = list_example_scripts()
    if not scripts:
        rprint("[yellow]No examples found.")
        raise typer.Exit(code=1)

    table = Table(title="AirSim Examples")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Path", style="magenta")
    for p in scripts:
        short, _ = extract_example_description(p)
        table.add_row(p.stem, short, str(p))
    rprint(table)


@app.command("describe")
def describe(
    name: str = typer.Argument(..., help="Example name (stem), e.g., hello_car"),
):
    """Show detailed description and path for an example."""
    load_env()
    target = None
    for p in list_example_scripts():
        if p.stem == name:
            target = p
            break
    if target is None:
        rprint(f"[red]Example not found: {name}")
        raise typer.Exit(code=1)

    short, long = extract_example_description(target)
    rprint(f"[bold cyan]{name}[/bold cyan]")
    rprint(f"[dim]{target}[/dim]")
    rprint("")
    rprint(long)


@app.command()
def run(
    name: str = typer.Argument(..., help="Example name (stem), e.g., hello_car"),
    yield_control: bool = typer.Option(
        False, "--yield-control", help="Yield control to keyboard after script."
    ),
    car_name: Optional[str] = typer.Option(
        None, help="Vehicle name override (defaults from .env CAR_NAME)."
    ),
):
    """Run an example by name and optionally yield control back to the simulator."""
    load_env()
    target = None
    for p in list_example_scripts():
        if p.stem == name:
            target = p
            break
    if target is None:
        rprint(f"[red]Example not found: {name}")
        raise typer.Exit(code=1)

    env = {}
    if car_name:
        env["CAR_NAME"] = car_name

    code = run_script(target, env)
    if code != 0:
        raise typer.Exit(code)

    if yield_control:
        # call root yield_control.py script in-process with env
        yc_path = ROOT / "yield_control.py"
        if yc_path.exists():
            rprint("[green]Yielding control back to keyboard...")
            rc = run_script(
                yc_path, {"CAR_NAME": car_name or os.getenv("CAR_NAME", "Car1")}
            )
            if rc != 0:
                raise typer.Exit(rc)
        else:
            rprint("[yellow]yield_control.py not found; skipping.")


@app.command("settings")
def settings_cmd(
    show: bool = typer.Option(False, "--show", help="Print current settings.json."),
    sim_mode: Optional[str] = typer.Option(
        None, "--sim-mode", help="Set SimMode (e.g., Car, ComputerVision)."
    ),
    vehicle: Optional[str] = typer.Option(
        None, "--vehicle", help="Vehicle key under Vehicles to modify (default: Car1)."
    ),
    enable_lidar: Optional[bool] = typer.Option(
        None, "--enable-lidar/--disable-lidar", help="Enable/disable Lidar360 sensor."
    ),
    lidar_rate: Optional[int] = typer.Option(
        None, "--lidar-pps", help="Lidar points per second."
    ),
    save: bool = typer.Option(False, "--save", help="Write changes to settings.json."),
):
    """View and tweak settings.json quickly from the CLI."""
    load_env()
    data = read_settings()
    if not data:
        raise typer.Exit(code=1)

    changed = False
    if sim_mode:
        data["SimMode"] = sim_mode
        changed = True

    vkey = vehicle or "Car1"
    if enable_lidar is not None or lidar_rate is not None:
        vehicles = data.setdefault("Vehicles", {})
        car = vehicles.setdefault(vkey, {})
        sensors = car.setdefault("Sensors", {})
        lidar = sensors.setdefault("Lidar360", {})
        if enable_lidar is not None:
            lidar["Enabled"] = bool(enable_lidar)
            changed = True
        if lidar_rate is not None:
            lidar["PointsPerSecond"] = int(lidar_rate)
            changed = True

    if show or not changed:
        rprint(json.dumps(data, indent=2))

    if save and changed:
        write_settings(data)
        rprint(f"[green]Saved changes to {SETTINGS_FILE}")


@app.command()
def yield_control(
    car_name: Optional[str] = typer.Option(
        None, help="Vehicle name (defaults from .env CAR_NAME)."
    ),
):
    """Yield control back to keyboard for the configured car."""
    load_env()
    yc_path = ROOT / "yield_control.py"
    if not yc_path.exists():
        rprint("[red]yield_control.py not found")
        raise typer.Exit(code=1)
    rc = run_script(yc_path, {"CAR_NAME": car_name or os.getenv("CAR_NAME", "Car1")})
    raise typer.Exit(rc)


@app.command("capture-images")
def capture_images(
    out_dir: Path = typer.Option(
        Path("data/images"),
        exists=False,
        dir_okay=True,
        file_okay=False,
        help="Output directory.",
    ),
    camera: str = typer.Option(
        "0", help="Camera name or index as string (per AirSim)."
    ),
    count: int = typer.Option(10, help="Number of frames to capture."),
    interval: float = typer.Option(0.5, help="Seconds between captures."),
    car_name: Optional[str] = typer.Option(
        None, help="Vehicle name; defaults to .env CAR_NAME."
    ),
):
    """Capture scene images from a camera and save PNGs."""
    load_env()
    out_dir.mkdir(parents=True, exist_ok=True)
    client = airsim.CarClient()
    client.confirmConnection()
    vname = car_name or os.getenv("CAR_NAME", "Car1")

    req = airsim.ImageRequest(
        camera, airsim.ImageType.Scene, pixels_as_float=False, compress=False
    )

    for i in range(count):
        responses = client.simGetImages([req], vehicle_name=vname)
        if not responses:
            rprint("[red]No image response")
            break
        img = responses[0]
        if img.height == 0 or img.width == 0:
            rprint("[yellow]Empty image response; skipping")
            time.sleep(interval)
            continue
        png_path = out_dir / f"{camera}_{i:05d}.png"
        airsim.write_png(str(png_path), img.image_data_uint8)
        rprint(f"[green]Saved {png_path}")
        time.sleep(interval)


@app.command("lidar-dump")
def lidar_dump(
    out_file: Path = typer.Option(
        Path("data/lidar/points.csv"), help="CSV output (x,y,z per row)."
    ),
    sensor_name: str = typer.Option(
        "Lidar360", help="Sensor key in settings (default: Lidar360)."
    ),
    car_name: Optional[str] = typer.Option(
        None, help="Vehicle name; defaults to .env CAR_NAME."
    ),
):
    """Grab a single lidar scan and dump to CSV."""
    load_env()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    client = airsim.CarClient()
    client.confirmConnection()
    vname = car_name or os.getenv("CAR_NAME", "Car1")

    data = client.getLidarData(lidar_name=sensor_name, vehicle_name=vname)
    if (
        not hasattr(data, "point_cloud")
        or not isinstance(data.point_cloud, (list, tuple))
        or len(data.point_cloud) < 3
    ):
        rprint("[yellow]No lidar points available")
        raise typer.Exit(code=1)

    pts = list(data.point_cloud)
    with out_file.open("w", encoding="utf-8") as f:
        f.write("x,y,z\n")
        for idx in range(0, len(pts), 3):
            x, y, z = pts[idx], pts[idx + 1], pts[idx + 2]
            f.write(f"{x},{y},{z}\n")
    rprint(f"[green]Wrote {out_file} ({len(pts) // 3} points)")


def main():  # console_script entry point
    load_env()
    app()


if __name__ == "__main__":
    main()
