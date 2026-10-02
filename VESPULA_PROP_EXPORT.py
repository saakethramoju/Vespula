from pathlib import Path
import re

import h5py
import numpy as np


def _safe_group_name(name):
    name = str(name).strip()
    name = re.sub(r"[\\/\x00]", "_", name)
    name = re.sub(r"\s+", "_", name)
    return name


def _find_network(h5):
    for name, group in h5.items():
        if isinstance(group, h5py.Group) and "transient" in group:
            return name

    raise ValueError("No FullFlow transient network found in HDF5 file.")


def _get_track(tracks, name):
    key = _safe_group_name(name)

    if key not in tracks:
        raise KeyError(
            f"Required FullFlow track '{name}' was not found. "
            f"Expected HDF5 dataset '{key}'."
        )

    return np.asarray(tracks[key], dtype=float)


def _cutoff_time(time, volume, threshold):
    indices = np.where(volume <= threshold)[0]

    if len(indices) == 0:
        return time[-1]

    i = indices[0]

    if i == 0:
        return time[0]

    t0 = time[i - 1]
    t1 = time[i]

    v0 = volume[i - 1]
    v1 = volume[i]

    if v1 == v0:
        return t1

    return t0 + (threshold - v0) * (t1 - t0) / (v1 - v0)


def _make_time_axis(time, cutoff):
    before_cutoff = time[time < cutoff]

    if np.isclose(cutoff, time).any():
        return time[time <= cutoff]

    return np.append(before_cutoff, cutoff)


def _write_curve(filename, time, values, header):
    data = np.column_stack((time, values))

    np.savetxt(
        filename,
        data,
        delimiter=",",
        header=f"Time (s),{header}",
        comments="",
        fmt="%.10g",
    )


def ExportRocketPyCurves(
    filename,
    output_directory="rocketpy_curves",
    tank_empty_volume=0.0,
):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    with h5py.File(filename, "r") as h5:

        network = _find_network(h5)

        run = h5[
            f"{network}/transient/runs/base"
        ]

        time = np.asarray(run["time"], dtype=float)
        tracks = run["tracks"]

        track_names = {
            "thrust": "Thrust [N]",

            "lox_liquid_mass": "LOX Liquid Mass [kg]",
            "fuel_liquid_mass": "Fuel Liquid Mass [kg]",

            "copv_gas_mass": "COPV Gas Mass [kg]",
            "lox_ullage_gas_mass": "LOX Ullage Gas Mass [kg]",
            "fuel_ullage_gas_mass": "Fuel Ullage Gas Mass [kg]",

            "lox_liquid_density": "LOX Liquid Density [kg/m3]",
            "fuel_liquid_density": "Fuel Liquid Density [kg/m3]",

            "copv_gas_density": "COPV Gas Density [kg/m3]",
            "lox_ullage_gas_density": "LOX Ullage Gas Density [kg/m3]",
            "fuel_ullage_gas_density": "Fuel Ullage Gas Density [kg/m3]",

            "lox_liquid_volume": "LOX Liquid Volume [m3]",
            "fuel_liquid_volume": "Fuel Liquid Volume [m3]",

            "lox_ullage_volume": "LOX Ullage Volume [m3]",
            "fuel_ullage_volume": "Fuel Ullage Volume [m3]",
        }

        curves = {
            name: _get_track(tracks, track)
            for name, track in track_names.items()
        }

    lox_cutoff = _cutoff_time(
        time,
        curves["lox_liquid_volume"],
        tank_empty_volume,
    )

    fuel_cutoff = _cutoff_time(
        time,
        curves["fuel_liquid_volume"],
        tank_empty_volume,
    )

    cutoff = min(lox_cutoff, fuel_cutoff)

    export_time = _make_time_axis(time, cutoff)

    for name in curves:
        curves[name] = np.interp(
            export_time,
            time,
            curves[name],
        )

    exports = {
        "thrust.csv": (
            curves["thrust"],
            "Thrust (N)",
        ),

        "lox_liquid_mass.csv": (
            curves["lox_liquid_mass"],
            "LOX Liquid Mass (kg)",
        ),

        "fuel_liquid_mass.csv": (
            curves["fuel_liquid_mass"],
            "Fuel Liquid Mass (kg)",
        ),

        "copv_gas_mass.csv": (
            curves["copv_gas_mass"],
            "COPV Gas Mass (kg)",
        ),

        "lox_ullage_gas_mass.csv": (
            curves["lox_ullage_gas_mass"],
            "LOX Ullage Gas Mass (kg)",
        ),

        "fuel_ullage_gas_mass.csv": (
            curves["fuel_ullage_gas_mass"],
            "Fuel Ullage Gas Mass (kg)",
        ),

        "lox_liquid_density.csv": (
            curves["lox_liquid_density"],
            "LOX Liquid Density (kg/m3)",
        ),

        "fuel_liquid_density.csv": (
            curves["fuel_liquid_density"],
            "Fuel Liquid Density (kg/m3)",
        ),

        "copv_gas_density.csv": (
            curves["copv_gas_density"],
            "COPV Gas Density (kg/m3)",
        ),

        "lox_ullage_gas_density.csv": (
            curves["lox_ullage_gas_density"],
            "LOX Ullage Gas Density (kg/m3)",
        ),

        "fuel_ullage_gas_density.csv": (
            curves["fuel_ullage_gas_density"],
            "Fuel Ullage Gas Density (kg/m3)",
        ),

        "lox_liquid_volume.csv": (
            curves["lox_liquid_volume"],
            "LOX Liquid Volume (m3)",
        ),

        "fuel_liquid_volume.csv": (
            curves["fuel_liquid_volume"],
            "Fuel Liquid Volume (m3)",
        ),

        "lox_ullage_volume.csv": (
            curves["lox_ullage_volume"],
            "LOX Ullage Volume (m3)",
        ),

        "fuel_ullage_volume.csv": (
            curves["fuel_ullage_volume"],
            "Fuel Ullage Volume (m3)",
        ),
    }

    for csv_name, (values, header) in exports.items():
        _write_curve(
            output_directory / csv_name,
            export_time,
            values,
            header,
        )

    combined_header = [
        "Time (s)",
        "Thrust (N)",
        "LOX Liquid Mass (kg)",
        "Fuel Liquid Mass (kg)",
        "COPV Gas Mass (kg)",
        "LOX Ullage Gas Mass (kg)",
        "Fuel Ullage Gas Mass (kg)",
        "LOX Liquid Density (kg/m3)",
        "Fuel Liquid Density (kg/m3)",
        "COPV Gas Density (kg/m3)",
        "LOX Ullage Gas Density (kg/m3)",
        "Fuel Ullage Gas Density (kg/m3)",
        "LOX Liquid Volume (m3)",
        "Fuel Liquid Volume (m3)",
        "LOX Ullage Volume (m3)",
        "Fuel Ullage Volume (m3)",
    ]

    combined_data = np.column_stack(
        (
            export_time,
            curves["thrust"],
            curves["lox_liquid_mass"],
            curves["fuel_liquid_mass"],
            curves["copv_gas_mass"],
            curves["lox_ullage_gas_mass"],
            curves["fuel_ullage_gas_mass"],
            curves["lox_liquid_density"],
            curves["fuel_liquid_density"],
            curves["copv_gas_density"],
            curves["lox_ullage_gas_density"],
            curves["fuel_ullage_gas_density"],
            curves["lox_liquid_volume"],
            curves["fuel_liquid_volume"],
            curves["lox_ullage_volume"],
            curves["fuel_ullage_volume"],
        )
    )

    np.savetxt(
        output_directory / "propulsion_curves.csv",
        combined_data,
        delimiter=",",
        header=",".join(combined_header),
        comments="",
        fmt="%.10g",
    )

    print(
        f"RocketPy propulsion curves exported to "
        f"'{output_directory}' through t = {cutoff:.4f} s."
    )

    return cutoff