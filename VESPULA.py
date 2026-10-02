from VESPULA_PROP_SYSTEM import VespulaPropSystem
from VESPULA_PROP_EXPORT import ExportRocketPyCurves
from VESPULA_DATA import *



# ---- Flight Sim Settings ---- #
MAX_TIMESTEP                = 0.02


# ---- Prop System Settings ---- #
PROP_SOLVE_PROP_SYSTEM      = False
PROP_FILENAME               = 'VESPULA_PROP_SYSTEM.h5'
PROP_GENERATE_CURVES        = True
PROP_CURVE_DIRECTORY        = "VESPULA_PROP_CURVES"
PROP_DT                     = 0.1
PROP_T_FINAL                = 30
PROP_BANG_BANG              = True
PROP_TANK_EMPTY_VOLUME      = 0.1 * L_TO_M3
PROP_VERBOSE                = True
PROP_STATISTICS             = True








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