from thermoprop import Propellant, Reactants, Equilibrium
import fullplot as fplt

from VESPULA_DATA import *


FILENAME = "VESPULA_CHAMBER_MAP.h5"

fuel = Propellant(
    "RP-1",
    temperature=FUEL_INITIAL_PROPELLANT_TEMPERATURE,
)

oxidizer = Propellant(
    "LOX",
    temperature=LOX_INITIAL_PROPELLANT_TEMPERATURE,
)


def chamber_products(chamber_pressure, mixture_ratio):

    reactants = Reactants(
        fuels=fuel,
        oxidizers=oxidizer,
        mixture_ratio=mixture_ratio,
    )

    gas = Equilibrium(
        reactants=reactants,
        pressure=chamber_pressure,
    )

    return {
        "temperature": gas.temperature,
        "gamma": gas.gamma,
        "gamma_s": gas.gamma_s,
        "gas_constant": gas.gas_constant,
        "density": gas.density,
        "enthalpy": gas.enthalpy,
        "internal_energy": gas.internal_energy,
    }


fplt.generate_map(
    FILENAME,
    group="chamber",
    axes=[
        fplt.Axis.linear(
            "chamber_pressure",
            start=50 * PSIA_TO_PA,
            stop=500 * PSIA_TO_PA,
            count=46,
            units="Pa",
        ),
        fplt.Axis.linear(
            "mixture_ratio",
            start=0.5,
            stop=4.0,
            count=36,
        ),
    ],
    evaluate=chamber_products,
    overwrite=True,
    raise_errors=True,
)