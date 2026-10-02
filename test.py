from __future__ import annotations

import math

from fullflow import *
from thermoprop import Fluid


# =============================================================================
# Units
# =============================================================================

PSIA_TO_PA = 6894.76


# =============================================================================
# Vespula data
# =============================================================================

# Propellant inventories / drains
LOX_INITIAL_MASS = 88.0          # kg
LOX_MASS_FLOW = 3.185            # kg/s, positive outflow
LOX_DENSITY = 1140.0             # kg/m^3
LOX_TANK_RADIUS = 0.1143         # m
LOX_TANK_HEIGHT = 2.1913619      # m

FUEL_INITIAL_MASS = 41.8         # kg
FUEL_MASS_FLOW = 1.593           # kg/s, positive outflow
FUEL_DENSITY = 805.0             # kg/m^3
FUEL_TANK_RADIUS = 0.1143        # m
FUEL_TANK_HEIGHT = 1.428973      # m

# COPV / GN2
PRESSURANT_INITIAL_MASS = 17.40  # kg
PRESSURANT_TANK_RADIUS = 0.10464999   # m
PRESSURANT_TANK_HEIGHT = 1.4023661    # m
COPV_INITIAL_TEMPERATURE = 300.0      # K

# Initial ullage gas temperatures.  Change these if you have better values.
LOX_ULLAGE_INITIAL_TEMPERATURE = 293.15   # K
FUEL_ULLAGE_INITIAL_TEMPERATURE = 293.15  # K

# -----------------------------------------------------------------------------
# FILL THESE FOUR VALUES WITH YOUR VESPULA ASSUMPTIONS / DATA.
# -----------------------------------------------------------------------------
LOX_TANK_PRESSURE = 357 * PSIA_TO_PA         # Pa, regulated ullage pressure
FUEL_TANK_PRESSURE = 416 * PSIA_TO_PA        # Pa, regulated ullage pressure
LOX_COLLAPSE_FACTOR = 1.2       # dimensionless, e.g. 1.0 means no correction
FUEL_COLLAPSE_FACTOR = 1.2      # dimensionless


# =============================================================================
# Solver controls
# =============================================================================

FILE_NAME = "vespula_pressurant_blowdown"
DT = 0.01
SAVE_DT = 0.01
EMPTY_FRACTION = 0.01  # stop when first tank reaches 1% initial propellant mass


# =============================================================================
# Helpers / validation
# =============================================================================

for name, value in {
    "LOX_TANK_PRESSURE": LOX_TANK_PRESSURE,
    "FUEL_TANK_PRESSURE": FUEL_TANK_PRESSURE,
    "LOX_COLLAPSE_FACTOR": LOX_COLLAPSE_FACTOR,
    "FUEL_COLLAPSE_FACTOR": FUEL_COLLAPSE_FACTOR,
}.items():
    if value is None:
        raise ValueError(f"Set {name} before running this script.")

if LOX_TANK_PRESSURE <= 0 or FUEL_TANK_PRESSURE <= 0:
    raise ValueError("Tank pressures must be positive.")
if LOX_COLLAPSE_FACTOR <= 0 or FUEL_COLLAPSE_FACTOR <= 0:
    raise ValueError("Collapse factors must be positive.")


def cylinder_volume(radius: float, height: float) -> float:
    return math.pi * radius**2 * height


LOX_TANK_VOLUME = cylinder_volume(LOX_TANK_RADIUS, LOX_TANK_HEIGHT)
FUEL_TANK_VOLUME = cylinder_volume(FUEL_TANK_RADIUS, FUEL_TANK_HEIGHT)
COPV_VOLUME = cylinder_volume(PRESSURANT_TANK_RADIUS, PRESSURANT_TANK_HEIGHT)

LOX_INITIAL_LIQUID_VOLUME = LOX_INITIAL_MASS / LOX_DENSITY
FUEL_INITIAL_LIQUID_VOLUME = FUEL_INITIAL_MASS / FUEL_DENSITY

LOX_INITIAL_ULLAGE_VOLUME = LOX_TANK_VOLUME - LOX_INITIAL_LIQUID_VOLUME
FUEL_INITIAL_ULLAGE_VOLUME = FUEL_TANK_VOLUME - FUEL_INITIAL_LIQUID_VOLUME

if LOX_INITIAL_ULLAGE_VOLUME <= 0:
    raise ValueError("LOX initial liquid volume exceeds the assumed tank volume.")
if FUEL_INITIAL_ULLAGE_VOLUME <= 0:
    raise ValueError("Fuel initial liquid volume exceeds the assumed tank volume.")

# Stop just before the first tank becomes empty.  With the current Vespula
# masses/flows, fuel is limiting and this is about 25.98 s for EMPTY_FRACTION=1%.
LOX_EMPTY_TIME = (1.0 - EMPTY_FRACTION) * LOX_INITIAL_MASS / LOX_MASS_FLOW
FUEL_EMPTY_TIME = (1.0 - EMPTY_FRACTION) * FUEL_INITIAL_MASS / FUEL_MASS_FLOW
T_FINAL = min(LOX_EMPTY_TIME, FUEL_EMPTY_TIME)

# Derive the initial COPV pressure from its mass, assumed volume, and temperature
# with ThermoProp's real-fluid GN2 EOS instead of assuming an ideal-gas pressure.
COPV_INITIAL_DENSITY = PRESSURANT_INITIAL_MASS / COPV_VOLUME
COPV_INITIAL_STATE = Fluid(
    "gn2",
    density=COPV_INITIAL_DENSITY,
    temperature=COPV_INITIAL_TEMPERATURE,
)
COPV_INITIAL_PRESSURE = COPV_INITIAL_STATE.pressure

# Initial ullage densities are useful only as nonlinear-solver mass-flow guesses.
LOX_ULLAGE_INITIAL_STATE = Fluid(
    "gn2",
    pressure=LOX_TANK_PRESSURE,
    temperature=LOX_ULLAGE_INITIAL_TEMPERATURE,
)
FUEL_ULLAGE_INITIAL_STATE = Fluid(
    "gn2",
    pressure=FUEL_TANK_PRESSURE,
    temperature=FUEL_ULLAGE_INITIAL_TEMPERATURE,
)

LOX_GN2_MDOT_GUESS = (
    LOX_COLLAPSE_FACTOR
    * LOX_ULLAGE_INITIAL_STATE.density
    * LOX_MASS_FLOW
    / LOX_DENSITY
)
FUEL_GN2_MDOT_GUESS = (
    FUEL_COLLAPSE_FACTOR
    * FUEL_ULLAGE_INITIAL_STATE.density
    * FUEL_MASS_FLOW
    / FUEL_DENSITY
)


# =============================================================================
# Custom constant-drain liquid inventory
# =============================================================================

class ConstantDrainInventory(Component):
    """Integrate a liquid mass with a prescribed positive outlet mass flow."""

    def __init__(
        self,
        name: str,
        network: Network,
        mass: State,
        mass_flow_out: State | float,
    ):
        self.mass_dot = 0.0
        self.setup()

    def evaluate_states(self):
        self.mass_dot = -self.mass_flow_out.value

    @property
    def dynamics(self):
        return [(self.mass, self.mass_dot)]


# =============================================================================
# Network and propellant inventories
# =============================================================================

VespulaBlowdown = Network("Vespula Pressurant Blowdown")

lox_mass = State(LOX_INITIAL_MASS, bounds=(0.0, None))
fuel_mass = State(FUEL_INITIAL_MASS, bounds=(0.0, None))

LOXInventory = ConstantDrainInventory(
    "LOX Inventory",
    VespulaBlowdown,
    mass=lox_mass,
    mass_flow_out=LOX_MASS_FLOW,
)
FuelInventory = ConstantDrainInventory(
    "Fuel Inventory",
    VespulaBlowdown,
    mass=fuel_mass,
    mass_flow_out=FUEL_MASS_FLOW,
)

# Physical liquid and ullage volumes.
lox_liquid_volume = lox_mass / LOX_DENSITY
fuel_liquid_volume = fuel_mass / FUEL_DENSITY

lox_ullage_volume = LOX_TANK_VOLUME - lox_liquid_volume
fuel_ullage_volume = FUEL_TANK_VOLUME - fuel_liquid_volume

# Empirical collapse-factor implementation.  Initial ullage volume is unchanged;
# only subsequent displaced propellant volume is multiplied by C.
lox_effective_ullage_volume = (
    LOX_INITIAL_ULLAGE_VOLUME
    + LOX_COLLAPSE_FACTOR * (lox_ullage_volume - LOX_INITIAL_ULLAGE_VOLUME)
)
fuel_effective_ullage_volume = (
    FUEL_INITIAL_ULLAGE_VOLUME
    + FUEL_COLLAPSE_FACTOR * (fuel_ullage_volume - FUEL_INITIAL_ULLAGE_VOLUME)
)


# =============================================================================
# COPV real-fluid GN2
# =============================================================================

COPVGas = Lookup(
    "COPV GN2",
    VespulaBlowdown,
    Fluid,
    "gn2",
    pressure=COPV_INITIAL_PRESSURE,
    temperature=COPV_INITIAL_TEMPERATURE,
)

# These are algebraic regulator-flow states.  FullFlow solves them each timestep
# so the corresponding ullage pressure stays at its set point.
gn2_lox_mass_flow = State(LOX_GN2_MDOT_GUESS, bounds=(0.0, None))
gn2_fuel_mass_flow = State(FUEL_GN2_MDOT_GUESS, bounds=(0.0, None))
gn2_total_mass_flow = gn2_lox_mass_flow + gn2_fuel_mass_flow

COPV = Volume(
    "COPV",
    VespulaBlowdown,
    volume=COPV_VOLUME,
    pressure=COPVGas.pressure,
    temperature=COPVGas.temperature,
    density=COPVGas.density,
    internal_energy=COPVGas.internal_energy,
    enthalpy=COPVGas.enthalpy,
    energy_variable="T",
    mass_flow_out=gn2_total_mass_flow,
)


# =============================================================================
# LOX ullage
# =============================================================================

LOXUllageGas = Lookup(
    "LOX Ullage GN2",
    VespulaBlowdown,
    Fluid,
    "gn2",
    pressure=LOX_TANK_PRESSURE,
    temperature=LOX_ULLAGE_INITIAL_TEMPERATURE,
)

LOXUllage = Volume(
    "LOX Ullage",
    VespulaBlowdown,
    volume=lox_effective_ullage_volume,
    pressure=LOXUllageGas.pressure,
    temperature=LOXUllageGas.temperature,
    density=LOXUllageGas.density,
    internal_energy=LOXUllageGas.internal_energy,
    enthalpy=LOXUllageGas.enthalpy,
    energy_variable="T",
    mass_flow_in=gn2_lox_mass_flow,
    total_enthalpy_in=COPVGas.enthalpy,
)

LOXRegulator = Balance(
    "LOX Ideal Regulator",
    VespulaBlowdown,
    variable=gn2_lox_mass_flow,
    function=LOXUllage.pressure - LOX_TANK_PRESSURE,
)


# =============================================================================
# Fuel ullage
# =============================================================================

FuelUllageGas = Lookup(
    "Fuel Ullage GN2",
    VespulaBlowdown,
    Fluid,
    "gn2",
    pressure=FUEL_TANK_PRESSURE,
    temperature=FUEL_ULLAGE_INITIAL_TEMPERATURE,
)

FuelUllage = Volume(
    "Fuel Ullage",
    VespulaBlowdown,
    volume=fuel_effective_ullage_volume,
    pressure=FuelUllageGas.pressure,
    temperature=FuelUllageGas.temperature,
    density=FuelUllageGas.density,
    internal_energy=FuelUllageGas.internal_energy,
    enthalpy=FuelUllageGas.enthalpy,
    energy_variable="T",
    mass_flow_in=gn2_fuel_mass_flow,
    total_enthalpy_in=COPVGas.enthalpy,
)

FuelRegulator = Balance(
    "Fuel Ideal Regulator",
    VespulaBlowdown,
    variable=gn2_fuel_mass_flow,
    function=FuelUllage.pressure - FUEL_TANK_PRESSURE,
)


# =============================================================================
# Tracks written to HDF5
# =============================================================================

# These are the two curves you want for RocketPy.
VespulaBlowdown.track("GN2 to LOX Mass Flow [kg/s]", gn2_lox_mass_flow)
VespulaBlowdown.track("GN2 to Fuel Mass Flow [kg/s]", gn2_fuel_mass_flow)

# Useful checks / diagnostics.
VespulaBlowdown.track("Total GN2 COPV Outflow [kg/s]", gn2_total_mass_flow)
VespulaBlowdown.track("COPV Mass [kg]", COPV.mass)
VespulaBlowdown.track("COPV Pressure [Pa]", COPV.pressure)
VespulaBlowdown.track("COPV Temperature [K]", COPV.temperature)
VespulaBlowdown.track("COPV Density [kg/m^3]", COPV.density)

VespulaBlowdown.track("LOX Mass [kg]", lox_mass)
VespulaBlowdown.track("Fuel Mass [kg]", fuel_mass)
VespulaBlowdown.track("LOX Physical Ullage Volume [m^3]", lox_ullage_volume)
VespulaBlowdown.track("Fuel Physical Ullage Volume [m^3]", fuel_ullage_volume)
VespulaBlowdown.track("LOX Effective Ullage Volume [m^3]", lox_effective_ullage_volume)
VespulaBlowdown.track("Fuel Effective Ullage Volume [m^3]", fuel_effective_ullage_volume)

VespulaBlowdown.track("LOX Ullage Pressure [Pa]", LOXUllage.pressure)
VespulaBlowdown.track("LOX Ullage Temperature [K]", LOXUllage.temperature)
VespulaBlowdown.track("LOX Ullage Density [kg/m^3]", LOXUllage.density)
VespulaBlowdown.track("Fuel Ullage Pressure [Pa]", FuelUllage.pressure)
VespulaBlowdown.track("Fuel Ullage Temperature [K]", FuelUllage.temperature)
VespulaBlowdown.track("Fuel Ullage Density [kg/m^3]", FuelUllage.density)


# =============================================================================
# Solve
# =============================================================================

print(f"Initial COPV volume: {COPV_VOLUME:.6f} m^3")
print(f"Initial COPV density: {COPV_INITIAL_DENSITY:.3f} kg/m^3")
print(f"Initial COPV pressure: {COPV_INITIAL_PRESSURE / PSIA_TO_PA:.1f} psia")
print(f"LOX initial ullage: {LOX_INITIAL_ULLAGE_VOLUME:.6f} m^3")
print(f"Fuel initial ullage: {FUEL_INITIAL_ULLAGE_VOLUME:.6f} m^3")
print(f"LOX 1% remaining time: {LOX_EMPTY_TIME:.3f} s")
print(f"Fuel 1% remaining time: {FUEL_EMPTY_TIME:.3f} s")
print(f"Transient final time: {T_FINAL:.3f} s")

Transient(VespulaBlowdown).solve(
    dt=DT,
    t_final=T_FINAL,
    filename=FILE_NAME,
    verbose=True,
    statistics=True
)

print(f"\nSaved: {FILE_NAME}.h5")
print("RocketPy curves:")
print("  GN2 to LOX Mass Flow [kg/s]")
print("  GN2 to Fuel Mass Flow [kg/s]")
print("Check that COPV pressure remains above both regulated tank pressures.")
