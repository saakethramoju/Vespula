from pathlib import Path

from rocketpy import (
    CylindricalTank,
    Environment,
    Flight,
    Fluid,
    LiquidMotor,
    MassFlowRateBasedTank,
    Rocket,
)

import VESPULA_DATA as D


BASE_DIR = Path(__file__).resolve().parent


def data_file(filename):
    return str(BASE_DIR / filename)


def build_environment():
    environment = Environment(elevation=D.LAUNCH_ELEVATION)
    environment.set_atmospheric_model(type="standard_atmosphere")
    return environment


def build_motor():
    lox = Fluid("LOX", D.LOX_DENSITY)
    fuel = Fluid("RP-1", D.FUEL_DENSITY)
    gn2_lox = Fluid("GN2 LOX Ullage", data_file(D.PRESSURANT_LOX_ULLAGE_DENSITY))
    gn2_fuel = Fluid("GN2 Fuel Ullage", data_file(D.PRESSURANT_FUEL_ULLAGE_DENSITY))
    gn2_copv = Fluid("GN2 COPV", data_file(D.PRESSURANT_COPV_DENSITY))

    lox_geometry = CylindricalTank(
        radius_function=D.LOX_TANK_RADIUS,
        height=D.LOX_TANK_HEIGHT,
    )
    fuel_geometry = CylindricalTank(
        radius_function=D.FUEL_TANK_RADIUS,
        height=D.FUEL_TANK_HEIGHT,
    )
    copv_geometry = CylindricalTank(
        radius_function=D.PRESSURANT_TANK_RADIUS,
        height=D.PRESSURANT_TANK_HEIGHT,
    )

    lox_tank = MassFlowRateBasedTank(
        name="LOX Tank",
        geometry=lox_geometry,
        flux_time=D.BURN_TIME,
        liquid=lox,
        gas=gn2_lox,
        initial_liquid_mass=D.LOX_INITIAL_MASS,
        initial_gas_mass=D.PRESSURANT_INITIAL_LOX_ULLAGE_MASS,
        liquid_mass_flow_rate_in=0.0,
        liquid_mass_flow_rate_out=D.LOX_MASS_FLOW,
        gas_mass_flow_rate_in=data_file(D.PRESSURANT_LOX_SIDE_MASS_FLOW),
        gas_mass_flow_rate_out=0.0,
        temperature=data_file(D.PRESSURANT_LOX_ULLAGE_TEMPERATURE),
        pressure=D.LOX_TANK_PRESSURE,
        discretize=500,
    )

    fuel_tank = MassFlowRateBasedTank(
        name="Fuel Tank",
        geometry=fuel_geometry,
        flux_time=D.BURN_TIME,
        liquid=fuel,
        gas=gn2_fuel,
        initial_liquid_mass=D.FUEL_INITIAL_MASS,
        initial_gas_mass=D.PRESSURANT_INITIAL_FUEL_ULLAGE_MASS,
        liquid_mass_flow_rate_in=0.0,
        liquid_mass_flow_rate_out=D.FUEL_MASS_FLOW,
        gas_mass_flow_rate_in=data_file(D.PRESSURANT_FUEL_SIDE_MASS_FLOW),
        gas_mass_flow_rate_out=0.0,
        temperature=data_file(D.PRESSURANT_FUEL_ULLAGE_TEMPERATURE),
        pressure=D.FUEL_TANK_PRESSURE,
        discretize=500,
    )

    copv_tank = MassFlowRateBasedTank(
        name="GN2 COPV",
        geometry=copv_geometry,
        flux_time=D.BURN_TIME,
        liquid=gn2_copv,
        gas=gn2_copv,
        initial_liquid_mass=0.0,
        initial_gas_mass=D.PRESSURANT_INITIAL_COPV_MASS,
        liquid_mass_flow_rate_in=0.0,
        liquid_mass_flow_rate_out=0.0,
        gas_mass_flow_rate_in=0.0,
        gas_mass_flow_rate_out=data_file(D.PRESSURANT_COPV_MASS_FLOW),
        temperature=data_file(D.PRESSURANT_COPV_TEMPERATURE),
        pressure=data_file(D.PRESSURANT_COPV_PRESSURE),
        discretize=500,
    )

    motor = LiquidMotor(
        thrust_source=data_file(D.THRUST_CURVE),
        dry_mass=D.ENGINE_MASS,
        dry_inertia=(
            D.ENGINE_I_XX,
            D.ENGINE_I_YY,
            D.ENGINE_I_ZZ,
            D.ENGINE_I_XY,
            D.ENGINE_I_XZ,
            D.ENGINE_I_YZ,
        ),
        nozzle_radius=D.NOZZLE_EXIT_RADIUS,
        center_of_dry_mass_position=D.ENGINE_CG_Z - D.NOZZLE_EXIT_Z,
        nozzle_position=0.0,
        burn_time=D.BURN_TIME,
        interpolation_method="linear",
        coordinate_system_orientation="nozzle_to_combustion_chamber",
        reference_pressure=D.THRUST_REFERENCE_PRESSURE,
    )

    motor.add_tank(lox_tank, D.LOX_TANK_Z - D.NOZZLE_EXIT_Z)
    motor.add_tank(fuel_tank, D.FUEL_TANK_Z - D.NOZZLE_EXIT_Z)
    motor.add_tank(copv_tank, D.PRESSURANT_TANK_Z - D.NOZZLE_EXIT_Z)

    return motor


def build_rocket(motor):
    rocket = Rocket(
        radius=D.VEHICLE_RADIUS,
        mass=D.VEHICLE_DRY_MASS,
        inertia=(
            D.I_XX_DRY,
            D.I_YY_DRY,
            D.I_ZZ_DRY,
            D.I_XY_DRY,
            D.I_XZ_DRY,
            D.I_YZ_DRY,
        ),
        power_off_drag=data_file(D.CD_POWER_OFF),
        power_on_drag=data_file(D.CD_POWER_ON),
        center_of_mass_without_motor=D.CG_Z_DRY,
        coordinate_system_orientation="tail_to_nose",
    )

    rocket.add_motor(motor, position=D.NOZZLE_EXIT_Z)

    rocket.add_nose(
        length=D.NOSECONE_LENGTH,
        kind=D.NOSECONE_TYPE,
        position=D.NOSECONE_Z,
    )

    rocket.add_trapezoidal_fins(
        n=D.FIN_COUNT,
        root_chord=D.FIN_ROOT_CHORD,
        tip_chord=D.FIN_TIP_CHORD,
        span=D.FIN_SPAN,
        sweep_length=D.FIN_SWEEP_LENGTH,
        position=D.FIN_Z,
        cant_angle=D.FIN_CANT_ANGLE,
    )

    return rocket


def run():
    environment = build_environment()
    motor = build_motor()
    rocket = build_rocket(motor)

    flight = Flight(
        rocket=rocket,
        environment=environment,
        rail_length=D.RAIL_LENGTH,
        inclination=D.RAIL_INCLINATION,
        heading=D.RAIL_HEADING,
        terminate_on_apogee=True,
        max_time=600,
        max_time_step=0.02,
        verbose=True,
    )

    flight.prints.out_of_rail_conditions()
    flight.prints.burn_out_conditions()
    flight.prints.apogee_conditions()

    flight.plots.linear_kinematics_data()
    flight.plots.aerodynamic_forces()
    flight.plots.stability_and_control_data()
    flight.plots.trajectory_3d()

    return flight


if __name__ == "__main__":
    flight = run()
