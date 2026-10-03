from pathlib import Path
import re
import h5py
import numpy as np
import warnings
from rocketpy import Function


def ExportFlightResults(flight, filename):
    time = np.asarray(flight.solution_array[:, 0], dtype=float)

    with h5py.File(filename, "w") as h5:
        flight_group = h5.create_group("flight")
        flight_group.attrs["description"] = "Vespula RocketPy 6-DOF Flight Results"
        flight_group.create_dataset("time", data=time)
        skipped = []

        for name in dir(flight):
            if name.startswith("_"):
                continue

            if name in ("solution", "solution_array", "time"):
                continue

            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    value = getattr(flight, name)

                    if caught:
                        skipped.append(name)
                        continue
            except Exception:
                skipped.append(name)
                continue

            if isinstance(value, Function):
                try:
                    inputs = value.get_inputs()
                    if len(inputs) != 1:
                        continue

                    input_name = str(inputs[0]).lower()
                    if "time" not in input_name and input_name not in ("t", "time"):
                        continue

                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        values = np.asarray([value(t) for t in time], dtype=float)

                        if caught:
                            skipped.append(name)
                            continue

                    dataset = flight_group.create_dataset(name, data=values)
                    outputs = value.get_outputs()
                    if len(outputs) > 0:
                        dataset.attrs["description"] = str(outputs[0])
                except Exception:
                    skipped.append(name)
                continue

            if isinstance(
                value,
                (bool, int, float, np.integer, np.floating),
            ):
                try:
                    flight_group.create_dataset(name, data=value)
                except Exception:
                    skipped.append(name)
                continue

        solution = np.asarray(flight.solution_array, dtype=float)
        raw_solution = flight_group.create_dataset("solution", data=solution)
        raw_solution.attrs["columns"] = (
            "time,x,y,z,vx,vy,vz,"
            "e0,e1,e2,e3,w1,w2,w3"
        )

        if skipped:
            flight_group.attrs["skipped_attributes"] = ", ".join(
                sorted(set(skipped))
            )

    print(f"Flight results exported to '{filename}'.")



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
        run = h5[f"{network}/transient/runs/base"]

        time = np.asarray(run["time"], dtype=float)
        tracks = run["tracks"]

        # Curves directly required by VESPULA.py / RocketPy.
        track_names = {
            "thrust": "Thrust [N]",

            "lox_liquid_mass": "LOX Liquid Mass [kg]",
            "fuel_liquid_mass": "Fuel Liquid Mass [kg]",

            "copv_gas_mass": "COPV Gas Mass [kg]",
            "lox_ullage_gas_mass": "LOX Ullage Gas Mass [kg]",
            "fuel_ullage_gas_mass": "Fuel Ullage Gas Mass [kg]",

            "copv_pressure": "COPV Pressure [Pa]",
            "copv_temperature": "COPV Temperature [K]",
            "lox_tank_pressure": "LOX Tank Pressure [Pa]",
            "lox_ullage_temperature": "LOX Ullage Temperature [K]",
            "fuel_tank_pressure": "Fuel Tank Pressure [Pa]",
            "fuel_ullage_temperature": "Fuel Ullage Temperature [K]",

            # Needed internally only to determine the exact cutoff.
            "lox_liquid_volume": "LOX Liquid Volume [m3]",
            "fuel_liquid_volume": "Fuel Liquid Volume [m3]",
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

    # Only the CSV files actually consumed by VESPULA.py.
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

        "copv_pressure.csv": (
            curves["copv_pressure"],
            "COPV Pressure (Pa)",
        ),

        "copv_temperature.csv": (
            curves["copv_temperature"],
            "COPV Temperature (K)",
        ),

        "lox_tank_pressure.csv": (
            curves["lox_tank_pressure"],
            "LOX Tank Pressure (Pa)",
        ),

        "lox_ullage_temperature.csv": (
            curves["lox_ullage_temperature"],
            "LOX Ullage Temperature (K)",
        ),

        "fuel_tank_pressure.csv": (
            curves["fuel_tank_pressure"],
            "Fuel Tank Pressure (Pa)",
        ),

        "fuel_ullage_temperature.csv": (
            curves["fuel_ullage_temperature"],
            "Fuel Ullage Temperature (K)",
        ),
    }

    for csv_name, (values, header) in exports.items():
        _write_curve(
            output_directory / csv_name,
            export_time,
            values,
            header,
        )

    # Clean out CSV files generated by older exporter versions that are no
    # longer used by the current RocketPy model.
    obsolete_exports = (
        "lox_liquid_density.csv",
        "fuel_liquid_density.csv",
        "copv_gas_density.csv",
        "lox_ullage_gas_density.csv",
        "fuel_ullage_gas_density.csv",
        "lox_liquid_volume.csv",
        "fuel_liquid_volume.csv",
        "lox_ullage_volume.csv",
        "fuel_ullage_volume.csv",
        "propulsion_curves.csv",
    )

    for csv_name in obsolete_exports:
        path = output_directory / csv_name
        if path.exists():
            path.unlink()

    print(
        f"RocketPy propulsion curves exported to "
        f"'{output_directory}' through t = {cutoff:.4f} s."
    )

    return cutoff
