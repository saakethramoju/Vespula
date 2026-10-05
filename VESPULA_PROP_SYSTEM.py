from thermoprop import *
from fullflow import *
import fullplot as fplt

from VESPULA_DATA import *

def VespulaPropSystem(dt:float = 0.1, 
                      t_final:float = 30,
                      filename:str = "VespulaPropSystem.h5", 
                      bang_bang:bool = True,
                      tank_empty_volume:float = 0.1 * L_TO_M3,
                      verbose:bool = False,
                      statistics:bool = False):


    # ---- Network ---- #
    Vespula = Network("Vespula Prop System")

    BANG_BANG = bang_bang




    # ---- Fluids ---- #
    COPVGas = Lookup(
        "COPV Pressurant Gas",
        Vespula,
        Fluid,
        "GN2",
        pressure=PRESSURANT_INITIAL_PRESSURE,
        temperature=PRESSURANT_INITIAL_TEMPERATURE
    )

    LOXUllageGas = Lookup(
        "LOX Tank Ullage",
        Vespula,
        Fluid,
        "GN2",
        pressure=LOX_TANK_PRESSURE,
        temperature=LOX_INITIAL_ULLAGE_TEMPERATURE
    )

    FuelUllageGas = Lookup(
        "Fuel Tank Ullage",
        Vespula,
        Fluid,
        "GN2",
        pressure=FUEL_TANK_PRESSURE,
        temperature=FUEL_INITIAL_ULLAGE_TEMPERATURE
    )

    LOXTankLiquid = Lookup(
        "LOX Tank Liquid",
        Vespula,
        Fluid,
        "LOX",
        pressure=LOX_TANK_PRESSURE,
        temperature=LOX_INITIAL_PROPELLANT_TEMPERATURE
    )

    FuelTankLiquid = Lookup(
        "Fuel Tank Liquid",
        Vespula,
        Propellant,
        "RP-1",
        pressure=FUEL_TANK_PRESSURE,
        temperature=FUEL_INITIAL_PROPELLANT_TEMPERATURE
    )

    LOXManifoldLiquid = Lookup(
        "LOX Injector Manifold Liquid",
        Vespula,
        Fluid,
        "LOX",
        pressure=LOX_INJECTOR_MANIFOLD_PRESSURE,
        temperature=LOX_INITIAL_PROPELLANT_TEMPERATURE
    )

    FuelManifoldLiquid = Lookup(
        "Fuel Injector Manifold Liquid",
        Vespula,
        Propellant,
        "RP-1",
        pressure=FUEL_INJECTOR_MANIFOLD_PRESSURE,
        temperature=FUEL_INITIAL_PROPELLANT_TEMPERATURE
    )






    # --- Sequences --- #
    def BangBang(t, pressure, bang_bang_state, 
                set_pressure, upper_limit, lower_limit):
        if pressure > set_pressure + upper_limit: return 0.0
        if pressure < set_pressure - lower_limit: return 1.0
        return bang_bang_state

    if BANG_BANG:

        LOX_BANG_BANG_STATE = State(0.0)
        FUEL_BANG_BANG_STATE = State(0.0)

        LOXBangBang = Sequence(
            "LOX Bang Bang",
            Vespula,
            target=LOX_BANG_BANG_STATE,
            function=BangBang,
            inputs=[LOXUllageGas.pressure, 
                    LOX_BANG_BANG_STATE, 
                    LOX_TANK_PRESSURE,
                    LOX_BANG_BANG_UPPER_LIMIT,
                    LOX_BANG_BANG_LOWER_LIMIT],
        )

        FuelBangBang = Sequence(
            "Fuel Bang Bang",
            Vespula,
            target=FUEL_BANG_BANG_STATE,
            function=BangBang,
            inputs=[FuelUllageGas.pressure, 
                    FUEL_BANG_BANG_STATE, 
                    FUEL_TANK_PRESSURE,
                    FUEL_BANG_BANG_UPPER_LIMIT,
                    FUEL_BANG_BANG_LOWER_LIMIT],
        )

    else:

        LOX_BANG_BANG_STATE = State(1.0)
        FUEL_BANG_BANG_STATE = State(1.0)




    def PressureRelief(t, pressure, set_pressure):
        if pressure > set_pressure : return 1.0
        return 0.0

    LOX_RELIEF_STATE = State(0.0)
    FUEL_RELIEF_STATE = State(0.0)

    LOXReliefCondition = Sequence(
        "LOX Relief Condition",
        Vespula,
        target=LOX_RELIEF_STATE,
        function=PressureRelief,
        inputs=[LOXUllageGas.pressure,
                LOX_RELIEF_PRESSURE]
    )

    FuelReliefCondition = Sequence(
        "Fuel Relief Condition",
        Vespula,
        target=FUEL_RELIEF_STATE,
        function=PressureRelief,
        inputs=[FuelUllageGas.pressure,
                FUEL_RELIEF_PRESSURE]
    )





    LOX_TANK_LIQUID_VOLUME = State(LOX_INITIAL_PROPELLANT_VOLUME)
    FUEL_TANK_LIQUID_VOLUME = State(FUEL_INITIAL_PROPELLANT_VOLUME)

    LOX_TANK_EMPTY_VOLUME = tank_empty_volume
    FUEL_TANK_EMPTY_VOLUME = tank_empty_volume

    LOXNearEmptyRedline = fplt.Trace(
        x=[0.0, 1.0e6],
        y=[LOX_TANK_EMPTY_VOLUME, LOX_TANK_EMPTY_VOLUME],
        name="LOX Tank Near Empty",
        role="redline",
    )

    FuelNearEmptyRedline = fplt.Trace(
        x=[0.0, 1.0e6],
        y=[FUEL_TANK_EMPTY_VOLUME, FUEL_TANK_EMPTY_VOLUME],
        name="Fuel Tank Near Empty",
        role="redline",
    )

    LOXTankVolumeSensor = Sensor(
        "LOX Tank Liquid Volume",
        Vespula,
        reading=LOX_TANK_LIQUID_VOLUME,
        conditions=LOXNearEmptyRedline,
    )

    FuelTankVolumeSensor = Sensor(
        "Fuel Tank Liquid Volume",
        Vespula,
        reading=FUEL_TANK_LIQUID_VOLUME,
        conditions=FuelNearEmptyRedline,
    )

    TankEmptyAbort = Sequence(
        "Tank Near Empty Abort",
        Vespula,
    )

    TankEmptyAbort.abort(
        condition=(LOXTankVolumeSensor, "LOX Tank Near Empty"),
        message="LOX tank reached near-empty volume.",
    )

    TankEmptyAbort.abort(
        condition=(FuelTankVolumeSensor, "Fuel Tank Near Empty"),
        message="Fuel tank reached near-empty volume.",
    )




    def HiFlowLoFlow(t, pressure, switch_pressure):
        if pressure < switch_pressure: return 1.0
        return 0.0

    LOX_HI_FLOW_STATE = State(0.0)
    FUEL_HI_FLOW_STATE = State(0.0)

    LOXSwitchCondition = Sequence(
        "LOX Switch Valve Condition",
        Vespula,
        target=LOX_HI_FLOW_STATE,
        function=HiFlowLoFlow,
        inputs=[COPVGas.pressure,
                LOX_SWITCH_PRESSURE]
    )

    FuelSwitchCondition = Sequence(
        "Fuel Switch Valve Condition",
        Vespula,
        target=FUEL_HI_FLOW_STATE,
        function=HiFlowLoFlow,
        inputs=[COPVGas.pressure,
                FUEL_SWITCH_PRESSURE]
    )










    # ---- Components ---- #
    COPV = Volume(
        "COPV",
        Vespula,
        pressure=COPVGas.pressure,
        temperature=COPVGas.temperature,
        volume=COPV_VOLUME,
        density=COPVGas.density,
        internal_energy=COPVGas.internal_energy,
        enthalpy=COPVGas.enthalpy,
        energy_variable='temperature'
    )

    LOXLo = CompressibleOrifice(
        "LOX-Side Lo-Flow Orifice",
        Vespula,
        upstream_total_pressure=COPV.pressure,
        upstream_total_temperature=COPV.temperature,
        downstream_pressure=LOXUllageGas.pressure,
        discharge_coefficient=LOX_BANG_BANG_STATE,
        cross_sectional_area=LOX_LO_FLOW_ORIFICE_AREA,
        gas_constant=COPVGas.gas_constant,
        specific_heat_ratio=COPVGas.specific_heat_ratio,
        upstream_static_enthalpy=COPV.enthalpy,
        upstream_static_temperature=COPV.temperature,
    )

    FuelLo = CompressibleOrifice(
        "Fuel-Side Lo-Flow Orifice",
        Vespula,
        upstream_total_pressure=COPV.pressure,
        upstream_total_temperature=COPV.temperature,
        downstream_pressure=FuelUllageGas.pressure,
        discharge_coefficient=FUEL_BANG_BANG_STATE,
        cross_sectional_area=FUEL_LO_FLOW_ORIFICE_AREA,
        gas_constant=COPVGas.gas_constant,
        specific_heat_ratio=COPVGas.specific_heat_ratio,
        upstream_static_enthalpy=COPV.enthalpy,
        upstream_static_temperature=COPV.temperature,
    )


    LOXHi = CompressibleOrifice(
        "LOX-Side Hi-Flow Orifice",
        Vespula,
        upstream_total_pressure=COPV.pressure,
        upstream_total_temperature=COPV.temperature,
        downstream_pressure=LOXUllageGas.pressure,
        discharge_coefficient=0.0,#LOX_BANG_BANG_STATE * LOX_HI_FLOW_STATE,
        cross_sectional_area=LOX_HI_FLOW_ORIFICE_AREA,
        gas_constant=COPVGas.gas_constant,
        specific_heat_ratio=COPVGas.specific_heat_ratio,
        upstream_static_enthalpy=COPV.enthalpy,
        upstream_static_temperature=COPV.temperature,
    )

    FuelHi = CompressibleOrifice(
        "Fuel-Side Hi-Flow Orifice",
        Vespula,
        upstream_total_pressure=COPV.pressure,
        upstream_total_temperature=COPV.temperature,
        downstream_pressure=FuelUllageGas.pressure,
        discharge_coefficient=FUEL_BANG_BANG_STATE * FUEL_HI_FLOW_STATE,
        cross_sectional_area=FUEL_HI_FLOW_ORIFICE_AREA,
        gas_constant=COPVGas.gas_constant,
        specific_heat_ratio=COPVGas.specific_heat_ratio,
        upstream_static_enthalpy=COPV.enthalpy,
        upstream_static_temperature=COPV.temperature,
    )


    COPV.mass_flow_out = (LOXLo.mass_flow + FuelLo.mass_flow + 
                        LOXHi.mass_flow + FuelHi.mass_flow)

    LOXTank = Volume(
        "LOX Tank Liquid Node",
        Vespula,
        pressure=LOXTankLiquid.pressure,
        volume=LOX_TANK_LIQUID_VOLUME,
        density=LOXTankLiquid.density,
    )

    FuelTank = Volume(
        "Fuel Tank Liquid Node",
        Vespula,
        pressure=FuelTankLiquid.pressure,
        volume=FUEL_TANK_LIQUID_VOLUME,
        density=FuelTankLiquid.density,
    )

    LOX_ULLAGE_VOLUME = LOX_TANK_VOLUME - LOXTank.volume
    FUEL_ULLAGE_VOLUME = FUEL_TANK_VOLUME - FuelTank.volume

    LOX_PRESSURANT_FLOW = LOXLo.mass_flow + LOXHi.mass_flow
    FUEL_PRESSURANT_FLOW = FuelLo.mass_flow + FuelHi.mass_flow

    LOX_EFFECTIVE_PRESSURANT_FLOW = LOX_PRESSURANT_FLOW / LOX_COLLAPSE_FACTOR
    FUEL_EFFECTIVE_PRESSURANT_FLOW = FUEL_PRESSURANT_FLOW / FUEL_COLLAPSE_FACTOR


    LOXUllage = Volume(
        "LOX Ullage",
        Vespula,
        pressure=LOXUllageGas.pressure,
        temperature=LOXUllageGas.temperature,
        volume=LOX_ULLAGE_VOLUME,
        density=LOXUllageGas.density,
        internal_energy=LOXUllageGas.internal_energy,
        enthalpy=LOXUllageGas.enthalpy,
        energy_variable="temperature",
        mass_flow_in=LOX_EFFECTIVE_PRESSURANT_FLOW,
        total_enthalpy_in=LOXLo.total_enthalpy,
    )

    FuelUllage = Volume(
        "Fuel Ullage",
        Vespula,
        pressure=FuelUllageGas.pressure,
        temperature=FuelUllageGas.temperature,
        volume=FUEL_ULLAGE_VOLUME,
        density=FuelUllageGas.density,
        internal_energy=FuelUllageGas.internal_energy,
        enthalpy=FuelUllageGas.enthalpy,
        energy_variable="temperature",
        mass_flow_in=FUEL_EFFECTIVE_PRESSURANT_FLOW,
        total_enthalpy_in=FuelLo.total_enthalpy,
    )


    LOXUllageBalance = Balance(
        "LOX Liquid Surface Pressure Balance",
        Vespula,
        variable=LOXTank.volume,
        function=LOXTank.pressure - LOXUllage.pressure,
    )

    FuelUllageBalance = Balance(
        "Fuel Liquid Surface Pressure Balance",
        Vespula,
        variable=FuelTank.volume,
        function=FuelTank.pressure - FuelUllage.pressure,
    )


    LOXRelief = CompressibleOrifice(
        "LOX Tank Relief Valve",
        Vespula,
        upstream_total_pressure=LOXUllage.pressure,
        upstream_total_temperature=LOXUllage.temperature,
        downstream_pressure=101325,
        discharge_coefficient=LOX_RELIEF_STATE,
        cross_sectional_area=LOX_RELIEF_CDA,
        gas_constant=LOXUllageGas.gas_constant,
        specific_heat_ratio=LOXUllageGas.gamma,
        mass_flow=LOXUllage.mass_flow_out,
    )

    FuelRelief = CompressibleOrifice(
        "Fuel Tank Relief Valve",
        Vespula,
        upstream_total_pressure=FuelUllage.pressure,
        upstream_total_temperature=FuelUllage.temperature,
        downstream_pressure=101325,
        discharge_coefficient=FUEL_RELIEF_STATE,
        cross_sectional_area=FUEL_RELIEF_CDA,
        gas_constant=FuelUllageGas.gas_constant,
        specific_heat_ratio=FuelUllageGas.gamma,
        mass_flow=FuelUllage.mass_flow_out,
    )


    LOXSystem = DischargeCoefficient(
        "LOX System CdA",
        Vespula,
        upstream_pressure=LOXTank.pressure,
        downstream_pressure=LOXManifoldLiquid.pressure,
        density=LOXTankLiquid.density,
        discharge_coefficient=1,
        cross_sectional_area=LOX_SYSTEM_CDA,
        mass_flow=LOXTank.mass_flow_out
    )

    FuelSystem = DischargeCoefficient(
        "Fuel System CdA",
        Vespula,
        upstream_pressure=FuelTank.pressure,
        downstream_pressure=FuelManifoldLiquid.pressure,
        density=FuelTankLiquid.density,
        discharge_coefficient=1,
        cross_sectional_area=FUEL_SYSTEM_CDA,
        mass_flow=FuelTank.mass_flow_out
    )

    LOXManifold = Volume(
        "LOX Injector Manifold",
        Vespula,
        pressure=LOXManifoldLiquid.pressure,
        mass_flow_in=LOXSystem.mass_flow
    )

    FuelManifold = Volume(
        "Fuel Injector Manifold",
        Vespula,
        pressure=FuelManifoldLiquid.pressure,
        mass_flow_in=FuelSystem.mass_flow
    )

    PC = State(CHAMBER_PRESSURE)

    LOXInjector = DischargeCoefficient(
        "LOX Injector CdA",
        Vespula,
        upstream_pressure=LOXManifold.pressure,
        downstream_pressure=PC,
        density=LOXManifoldLiquid.density,
        discharge_coefficient=1,
        cross_sectional_area=LOX_INJECTOR_CDA,
        mass_flow=LOXManifold.mass_flow_out,
    )

    FuelInjector = DischargeCoefficient(
        "Fuel Injector CdA",
        Vespula,
        upstream_pressure=FuelManifold.pressure,
        downstream_pressure=PC,
        density=FuelManifoldLiquid.density,
        discharge_coefficient=1,
        cross_sectional_area=FUEL_INJECTOR_CDA,
        mass_flow=FuelManifold.mass_flow_out,
    )

    MR = LOXInjector.mass_flow / FuelInjector.mass_flow

    ChamberGas = Map.from_hdf5(
        "Combustion Chamber Gas",
        Vespula,
        "vespula_chamber_map.h5",
        group="chamber",
        inputs={
            "chamber_pressure": PC,
            "mixture_ratio": MR,
        },
    )

    Chamber = Volume(
        "Combustion Chamber",
        Vespula,
        pressure=PC,
        mass_flow_in=LOXInjector.mass_flow + FuelInjector.mass_flow,
    )

    Nozzle = IsentropicNozzle(
        "Nozzle",
        Vespula,
        upstream_total_pressure=Chamber.pressure,
        upstream_total_temperature=ChamberGas.temperature,
        ambient_pressure=NOZZLE_EXIT_PRESSURE,
        specific_heat_ratio=ChamberGas.gamma,
        gas_constant=ChamberGas.gas_constant,
        throat_area=THROAT_AREA,
        expansion_ratio=EXPANSION_RATIO,
    )

    Chamber.mass_flow_out = Nozzle.mass_flow / CSTAR_EFFICIENCY
    THRUST = Nozzle.mass_flow * Nozzle.exit_velocity







    # ---- Tracked States ---- #
    Vespula.track("COPV Pressure [psia]", COPV.pressure / PSIA_TO_PA)
    Vespula.track("COPV Pressure [Pa]", COPV.pressure)
    Vespula.track("COPV Temperature [K]", COPV.temperature)
    Vespula.track("COPV Gas Mass [kg]", COPV.mass)
    Vespula.track("COPV Gas Density [kg/m3]", COPV.density)

    Vespula.track("LOX Tank Pressure [psia]", LOXUllageGas.pressure / PSIA_TO_PA)
    Vespula.track("LOX Tank Pressure [Pa]", LOXUllageGas.pressure)
    Vespula.track("LOX Liquid Mass [kg]", LOXTank.mass)
    Vespula.track("LOX Liquid Density [kg/m3]", LOXTank.density)
    Vespula.track("LOX Liquid Volume [L]", LOXTank.volume / L_TO_M3)
    Vespula.track("LOX Liquid Volume [m3]", LOXTank.volume)
    Vespula.track("LOX Ullage Gas Mass [kg]", LOXUllage.mass)
    Vespula.track("LOX Ullage Gas Density [kg/m3]", LOXUllage.density)
    Vespula.track("LOX Ullage Temperature [K]", LOXUllageGas.temperature)
    Vespula.track("LOX Ullage Volume [m3]", LOXUllage.volume)
    Vespula.track("LOX Bang Bang State", LOX_BANG_BANG_STATE)
    Vespula.track("LOX Hi Flow Switch State", LOX_HI_FLOW_STATE)
    Vespula.track("LOX Relief Valve State", LOX_RELIEF_STATE)
    Vespula.track("LOX Injector Mass Flow [kg/s]", LOXInjector.mass_flow)

    Vespula.track("Fuel Tank Pressure [psia]", FuelUllageGas.pressure / PSIA_TO_PA)
    Vespula.track("Fuel Tank Pressure [Pa]", FuelUllageGas.pressure)
    Vespula.track("Fuel Liquid Mass [kg]", FuelTank.mass)
    Vespula.track("Fuel Liquid Density [kg/m3]", FuelTank.density)
    Vespula.track("Fuel Liquid Volume [L]", FuelTank.volume / L_TO_M3)
    Vespula.track("Fuel Liquid Volume [m3]", FuelTank.volume)
    Vespula.track("Fuel Ullage Gas Mass [kg]", FuelUllage.mass)
    Vespula.track("Fuel Ullage Gas Density [kg/m3]", FuelUllage.density)
    Vespula.track("Fuel Ullage Temperature [K]", FuelUllageGas.temperature)
    Vespula.track("Fuel Ullage Volume [m3]", FuelUllage.volume)
    Vespula.track("Fuel Bang Bang State", FUEL_BANG_BANG_STATE)
    Vespula.track("Fuel Hi Flow Switch State", FUEL_HI_FLOW_STATE)
    Vespula.track("Fuel Relief Valve State", FUEL_RELIEF_STATE)
    Vespula.track("Fuel Injector Mass Flow [kg/s]", FuelInjector.mass_flow)

    Vespula.track("Mixture Ratio", MR)
    Vespula.track("Chamber Pressure [psia]", Chamber.pressure / PSIA_TO_PA)
    Vespula.track("Chamber Pressure [Pa]", Chamber.pressure)
    Vespula.track("Chamber Temperature [K]", ChamberGas.temperature)
    Vespula.track("Nozzle Mass Flow [kg/s]", Nozzle.mass_flow)
    Vespula.track("Thrust [lbf]", THRUST / LBF_TO_N)
    Vespula.track("Thrust [N]", THRUST)
        




    # ---- Solver ---- #
    Transient(Vespula).solve(
        dt=dt,
        t_final=t_final,
        filename=filename,
        verbose=verbose,
        statistics=statistics,
    )