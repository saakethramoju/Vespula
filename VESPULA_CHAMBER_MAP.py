from thermoprop import Propellant, Reactants, Equilibrium
import fullplot as fplt

from VESPULA_DATA import *


def VespulaChamberMap(filename: str ="VESPULA_CHAMBER_MAP.h5",
                      lox_temperature: float = LOX_INITIAL_PROPELLANT_TEMPERATURE,
                      fuel_temperature: float = FUEL_INITIAL_PROPELLANT_TEMPERATURE,
                      chamber_pressure_lower_limit: float = 50 * PSIA_TO_PA,
                      chamber_pressure_upper_limit: float = 500 * PSIA_TO_PA,
                      chamber_pressure_data_points: int = 46,
                      mixture_ratio_lower_limit: float = 0.5,
                      mixture_ratio_upper_limit: float = 4.0,
                      mixture_ratio_data_points: int = 36
                      ):
        
    FILENAME = filename

    fuel = Propellant(
        "RP-1",
        temperature=fuel_temperature,
    )

    oxidizer = Propellant(
        "LOX",
        temperature=lox_temperature,
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
                start=chamber_pressure_lower_limit,
                stop=chamber_pressure_upper_limit,
                count=chamber_pressure_data_points,
                units="Pa",
            ),
            fplt.Axis.linear(
                "mixture_ratio",
                start=mixture_ratio_lower_limit,
                stop=mixture_ratio_upper_limit,
                count=mixture_ratio_data_points,
            ),
        ],
        evaluate=chamber_products,
        overwrite=True,
        raise_errors=True,
    )