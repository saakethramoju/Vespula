import numpy as np
import thermoprop
from rocketpy import (
    Environment,
    CylindricalTank,
    Fluid,
    MassBasedTank,
    LiquidMotor,
    Rocket,
    Flight
)
from Vespula_Prop_System import VespulaPropSystem
from Vespula_Chamber_Map import VespulaChamberMap
from Vespula_Export import ExportRocketPyCurves, ExportFlightResults
from VESPULA_DATA import *
from Vespula_Canted_Flight import CantedThrustFlight




# ---- Flight Sim Settings ---- #
RUN_FLIGHT                  = True
MAX_TIMESTEP                = 0.02
MAX_TIME                    = 600
TERMINATE_ON_APOGEE         = True
ROTATING_EARTH              = False
WIND_ACTIVE                 = True
WIND_U_FILENAME             = "WIND_PROFILES/sizer_wind_u.csv"
WIND_V_FILENAME             = "WIND_PROFILES/sizer_wind_v.csv"
CD_POWER_ON                 = "VESPULA_DRAG_CURVES/sizer_drag_power_on.csv" # Cd = f(M, alpha, beta)
CD_POWER_OFF                = "VESPULA_DRAG_CURVES/sizer_drag_power_off.csv"
THRUST_MISALIGNMENT_ACTIVE  = True
EXPORT_RESULTS              = True
RESULTS_FILENAME            = "Vespula_6DOF_Results.h5"


# ---- Prop System Settings ---- #
PROP_GENERATE_CHAMBER_MAP   = False
PROP_CHAMBER_MAP_FILEANAME  = "VESPULA_CHAMBER_MAP.h5"
PROP_SOLVE_PROP_SYSTEM      = False
PROP_FILENAME               = 'VESPULA_PROP_SYSTEM.h5'
PROP_GENERATE_CURVES        = False
PROP_CURVE_DIRECTORY        = "VESPULA_PROP_CURVES"
PROP_DT                     = 0.1
PROP_T_FINAL                = 30
PROP_BANG_BANG              = False # check before generating curves
PROP_TANK_EMPTY_VOLUME      = 0.1 * L_TO_M3
PROP_VERBOSE                = True
PROP_STATISTICS             = True







# ---- Prop System ---- #
if PROP_GENERATE_CHAMBER_MAP:

    print("Generating chamber Pc/MR map...")

    VespulaChamberMap(
        filename=PROP_CHAMBER_MAP_FILEANAME,
        fuel_temperature=FUEL_INITIAL_PROPELLANT_TEMPERATURE,
        lox_temperature=LOX_INITIAL_PROPELLANT_TEMPERATURE
    )




if PROP_SOLVE_PROP_SYSTEM:

    print("Solving propulsion system...")

    VespulaPropSystem(
        dt=PROP_DT,
        t_final=PROP_T_FINAL,
        filename=PROP_FILENAME,
        bang_bang=PROP_BANG_BANG,
        tank_empty_volume=PROP_TANK_EMPTY_VOLUME,
        verbose=PROP_VERBOSE,
        statistics=PROP_STATISTICS,
    )




if PROP_GENERATE_CURVES:

    print("Generating propulsion system curves...")

    ExportRocketPyCurves(
        filename=PROP_FILENAME,
        output_directory=PROP_CURVE_DIRECTORY,
        tank_empty_volume=PROP_TANK_EMPTY_VOLUME,
    )




# ---- Launch Conditions ---- #
LaunchConditions = Environment(
    date=(YEAR, MONTH, DAY, HOUR),
    latitude=LATITUDE,
    longitude=LONGITUDE,
    elevation=LAUNCH_ELEVATION,
    timezone=TIMEZONE,
    datum="WGS84",
)

if not ROTATING_EARTH:
    LaunchConditions.earth_rotation_vector = [0.0, 0.0, 0.0]

if WIND_ACTIVE:
    LaunchConditions.set_atmospheric_model(
        type="custom_atmosphere",
        wind_u=WIND_U_FILENAME,
        wind_v=WIND_V_FILENAME,
    )





# ---- Motor Definition ---- #
BURN_TIME = np.loadtxt(f"{PROP_CURVE_DIRECTORY}/thrust.csv", delimiter=",", skiprows=1)[-1, 0]

def GN2Density(T, P):
    GN2 = thermoprop.Fluid(
        fluid="Nitrogen",
        temperature=T,
        pressure=P,
    )
    return GN2.density

def LOXDensity(T, P):
    LOX = thermoprop.Fluid(
        fluid="LOX",
        temperature=LOX_INITIAL_PROPELLANT_TEMPERATURE,
        pressure=P,
    )
    return LOX.density


def FuelDensity(T, P):
    RP1 = thermoprop.Propellant(
        "RP-1",
        temperature=FUEL_INITIAL_PROPELLANT_TEMPERATURE,
        pressure=P,
    )
    return RP1.density

# Adjusted tank heights to make volume and radius align
COPV_HEIGHT = COPV_VOLUME * (1 + 1e-8)/ (np.pi * COPV_RADIUS**2)
LOX_TANK_HEIGHT = LOX_TANK_VOLUME  * (1 + 2e-6) / (np.pi * LOX_TANK_RADIUS**2)
FUEL_TANK_HEIGHT = FUEL_TANK_VOLUME * (1 + 1e-8) / (np.pi * FUEL_TANK_RADIUS**2)

COPVTankGeometry = CylindricalTank(
    radius_function=COPV_RADIUS,
    height=COPV_HEIGHT,
    spherical_caps=False,
)

LOXTankGeometry = CylindricalTank(
    radius_function=LOX_TANK_RADIUS,
    height=LOX_TANK_HEIGHT,
    spherical_caps=False,
)

FuelTankGeometry = CylindricalTank(
    radius_function=FUEL_TANK_RADIUS,
    height=FUEL_TANK_HEIGHT,
    spherical_caps=False,
)

Pressurant = Fluid(
    name="GN2",
    density=GN2Density,
)

LOXPropellant = Fluid(
    name="LOX",
    density=LOXDensity,
)

FuelPropellant = Fluid(
    name="RP-1",
    density=FuelDensity,
)

COPVTank = MassBasedTank(
    name="COPV",
    geometry=COPVTankGeometry,
    flux_time=BURN_TIME,
    liquid=Fluid("Plutonium", density=1.0),
    gas=Pressurant,
    liquid_mass=0.0,
    gas_mass=f"{PROP_CURVE_DIRECTORY}/copv_gas_mass.csv",
    temperature=f"{PROP_CURVE_DIRECTORY}/copv_temperature.csv",
    pressure=f"{PROP_CURVE_DIRECTORY}/copv_pressure.csv",
)

LOXTank = MassBasedTank(
    name="LOX Tank",
    geometry=LOXTankGeometry,
    flux_time=BURN_TIME,
    liquid=LOXPropellant,
    gas=Pressurant,
    liquid_mass=f"{PROP_CURVE_DIRECTORY}/lox_liquid_mass.csv",
    gas_mass=f"{PROP_CURVE_DIRECTORY}/lox_ullage_gas_mass.csv",
    temperature=f"{PROP_CURVE_DIRECTORY}/lox_ullage_temperature.csv",
    pressure=f"{PROP_CURVE_DIRECTORY}/lox_tank_pressure.csv",
    discretize=None,
)

FuelTank = MassBasedTank(
    name="Fuel Tank",
    geometry=FuelTankGeometry,
    flux_time=BURN_TIME,
    liquid=FuelPropellant,
    gas=Pressurant,
    liquid_mass=f"{PROP_CURVE_DIRECTORY}/fuel_liquid_mass.csv",
    gas_mass=f"{PROP_CURVE_DIRECTORY}/fuel_ullage_gas_mass.csv",
    temperature=f"{PROP_CURVE_DIRECTORY}/fuel_ullage_temperature.csv",
    pressure=f"{PROP_CURVE_DIRECTORY}/fuel_tank_pressure.csv",
    discretize=None,
)


VespulaEngine = LiquidMotor(
    thrust_source=f"{PROP_CURVE_DIRECTORY}/thrust.csv",
    dry_mass=ENGINE_MASS,
    dry_inertia=(
        ENGINE_I_XX,
        ENGINE_I_YY,
        ENGINE_I_ZZ,
    ),
    nozzle_radius=np.sqrt(NOZZLE_EXIT_AREA / np.pi),
    center_of_dry_mass_position=ENGINE_CG_Z - NOZZLE_EXIT_Z,
    nozzle_position=0.0,
    burn_time=BURN_TIME,
    coordinate_system_orientation="nozzle_to_combustion_chamber",
)

VespulaEngine.add_tank(
    tank=LOXTank,
    position=LOX_TANK_Z - NOZZLE_EXIT_Z,
)

VespulaEngine.add_tank(
    tank=FuelTank,
    position=FUEL_TANK_Z - NOZZLE_EXIT_Z,
)

VespulaEngine.add_tank(
    tank=COPVTank,
    position=COPV_Z - NOZZLE_EXIT_Z,
)







# ---- Rocket Definition ---- #

Vespula = Rocket(
    radius=VEHICLE_RADIUS,
    mass=VEHICLE_DRY_MASS,
    inertia=(
        I_XX_DRY,
        I_YY_DRY,
        I_ZZ_DRY,
        I_XY_DRY,
        I_XZ_DRY,
        I_YZ_DRY,
    ),
    power_off_drag=CD_POWER_OFF,
    power_on_drag=CD_POWER_ON,
    center_of_mass_without_motor=CG_Z_DRY,
    coordinate_system_orientation="tail_to_nose",
)

Vespula.add_motor(
    motor=VespulaEngine,
    position=NOZZLE_EXIT_Z,
)

Vespula.add_nose(
    length=NOSECONE_LENGTH,
    kind=NOSECONE_TYPE,
    position=NOSECONE_Z,
)


Vespula.add_trapezoidal_fins(
    n=FIN_COUNT,
    root_chord=FIN_ROOT_CHORD,
    tip_chord=FIN_TIP_CHORD,
    span=FIN_SPAN,
    position=FIN_Z,
    sweep_length=FIN_SWEEP_LENGTH,
    cant_angle=FIN_CANT_ANGLE,
)







# ---- Flight Simulation ---- #
if RUN_FLIGHT:
    FlightModel = CantedThrustFlight if THRUST_MISALIGNMENT_ACTIVE else Flight

    flight_kwargs = dict(
        rocket=Vespula,
        environment=LaunchConditions,
        rail_length=RAIL_LENGTH,
        inclination=RAIL_INCLINATION,
        heading=RAIL_HEADING,
        max_time_step=MAX_TIMESTEP,
        max_time=MAX_TIME,
        terminate_on_apogee=TERMINATE_ON_APOGEE,
    )

    if THRUST_MISALIGNMENT_ACTIVE:
        VespulaFlight = FlightModel(
            **flight_kwargs,
            thrust_misalignment_angle=THRUST_MISALIGNMENT_ANGLE,
        )
    else:
        VespulaFlight = FlightModel(**flight_kwargs)


    VespulaFlight.plots.trajectory_3d()
    VespulaFlight.prints.all()

    if EXPORT_RESULTS:
        ExportFlightResults(
            flight=VespulaFlight,
            filename=RESULTS_FILENAME,
        )