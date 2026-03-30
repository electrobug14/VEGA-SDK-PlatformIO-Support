"""
build_vega.py — Multi-Project Aware Script
Detects subfolders in src/ and outputs binaries back to the project folder.
"""

Import("env")

import os
import platform
import subprocess
import shutil
from pathlib import Path

# -----------------------------------------------------------------------
# OS Detection & Tool Naming
# -----------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"
suffix = ".exe" if IS_WINDOWS else ""

def get_required_path(option_name):
    env_var_name = f"PLATFORMIO_{option_name.upper()}"
    env_val = os.environ.get(env_var_name)
    if env_val:
        return Path(env_val).resolve()
    
    path_str = env.GetProjectOption(option_name, "").strip()
    if not path_str:
        raise SystemExit(f"ERROR: '{option_name}' is not set.")
    return Path(path_str).resolve()

SDK_PATH  = get_required_path("vega_sdk_path")
TOOLS_BIN = get_required_path("vega_tools_path")

# Binary names adjust for Linux/Codespaces vs Windows
TOOL_PREFIX = "riscv64-unknown-elf-" if not IS_WINDOWS else "riscv64-vega-elf-"
GCC     = str(TOOLS_BIN / f"{TOOL_PREFIX}gcc{suffix}").replace("\\", "/")
OBJCOPY = str(TOOLS_BIN / f"{TOOL_PREFIX}objcopy{suffix}").replace("\\", "/")

# -----------------------------------------------------------------------
# Multi-Project Detection Logic
# -----------------------------------------------------------------------
SRC_DIR = Path(env.subst("$PROJECT_SRC_DIR")).resolve()

# Find the first subdirectory in src/ that contains a .c file
# This assumes you only build ONE project folder at a time.
project_subdirs = [d for d in SRC_DIR.iterdir() if d.is_dir() and list(d.glob("*.c"))]

if not project_subdirs:
    # Fallback to root src/ if no subfolders found
    ACTIVE_PROJECT_PATH = SRC_DIR
    print("[VEGA] Building from root src/ directory.")
else:
    # Pick the first one (or you could filter by an environment variable)
    ACTIVE_PROJECT_PATH = project_subdirs[0]
    print(f"[VEGA] Detected Project Folder: {ACTIVE_PROJECT_PATH.name}")

# -----------------------------------------------------------------------
# Compilation Flags
# -----------------------------------------------------------------------
BSP_DIR     = SDK_PATH / "bsp"
INC_DIR     = BSP_DIR / "include"
LD_SCRIPT   = str(BSP_DIR / "common" / "mbl.lds").replace("\\", "/")
STDLIB_C    = str(BSP_DIR / "common" / "stdlib.c")
RAWFLOAT_C  = str(BSP_DIR / "common" / "rawfloat.c")
CRT_S       = str(BSP_DIR / "common" / "crt.S")
DRIVER_SRCS = list((BSP_DIR / "drivers").rglob("*.c"))

INCS    = f"-I{str(INC_DIR)} -I{str(BSP_DIR)} -I{str(ACTIVE_PROJECT_PATH)}"
ARCH    = "-march=rv32im -mabi=ilp32 -mcmodel=medany"
DEFS    = "-DTHEJAS32"
OPT     = "-O0 -g -fno-builtin-printf -fno-common -fno-pic"
C_FLAGS = f"{ARCH} {INCS} {DEFS} {OPT} -include {str(INC_DIR)}/stdlib.h"
LDFLAGS = f"-nostartfiles -T{LD_SCRIPT} --specs=nano.specs -specs=nosys.specs -Wl,--gc-sections"
LIBS    = f"-L{str(BSP_DIR)} -Wl,--start-group -lvega -lc -lgcc -lm -Wl,--end-group"

build_dir = Path(env.subst("$BUILD_DIR")).resolve()
obj_dir   = build_dir / "vega_objs"
obj_dir.mkdir(parents=True, exist_ok=True)

def build_obj(src, obj):
    if not Path(obj).exists() or Path(src).stat().st_mtime > Path(obj).stat().st_mtime:
        Path(obj).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(f'"{GCC}" {C_FLAGS} -c "{str(src)}" -o "{obj}"', shell=True, check=True)
    return env.File(str(obj))

# 1. BSP
bsp_objs = [build_obj(s, obj_dir / "bsp" / f"{s.stem}.o") for s in DRIVER_SRCS + [Path(STDLIB_C), Path(RAWFLOAT_C)]]
crt_o = obj_dir / "bsp" / "crt.o"
subprocess.run(f'"{GCC}" {ARCH} {INCS} -c "{CRT_S}" -o "{crt_o}"', shell=True, check=True)
bsp_objs.insert(0, env.File(str(crt_o)))

# 2. Project Files
user_objs = [build_obj(s, obj_dir / "user" / f"{s.stem}.o") for s in ACTIVE_PROJECT_PATH.glob("*.c")]

env.Replace(PROGNAME="firmware", PROGSUFFIX=".elf")
env.Append(PIOBUILDFILES=user_objs + bsp_objs)
env["SRC_FILTER"] = "-<*>"
env.Replace(LINKCOM = f'"{GCC}" {ARCH} {LDFLAGS} -o $TARGET $SOURCES {LIBS}')

# -----------------------------------------------------------------------
# Post-Action: Copy binaries to Project Folder
# -----------------------------------------------------------------------
def move_binaries_to_project(source, target, env):
    elf_path = Path(target[0].get_abspath())
    bin_path = elf_path.with_suffix(".bin")
    hex_path = elf_path.with_suffix(".hex")

    # Generate BIN and HEX
    subprocess.run(f'"{OBJCOPY}" -O binary "{elf_path}" "{bin_path}"', shell=True, check=True)
    subprocess.run(f'"{OBJCOPY}" -O ihex "{elf_path}" "{hex_path}"', shell=True, check=True)

    # Copy to the specific Project Folder inside src/
    for ext_file in [elf_path, bin_path, hex_path]:
        dest = ACTIVE_PROJECT_PATH / ext_file.name
        shutil.copy2(ext_file, dest)
        print(f"[VEGA] Success! Copied to: {dest}")

env.AddPostAction("$BUILD_DIR/${PROGNAME}.elf", move_binaries_to_project)
