"""
build_vega.py — Cross-Platform PlatformIO extra_script (pre)
Fixed for Linux (Codespaces/GitHub Actions) and Windows compatibility.
"""

Import("env")

import os
import platform
import subprocess
from pathlib import Path

# -----------------------------------------------------------------------
# OS Detection & Tool Naming
# -----------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"
suffix = ".exe" if IS_WINDOWS else ""

# -----------------------------------------------------------------------
# Path Resolution (Env Var first for Cloud, then platformio.ini for Local)
# -----------------------------------------------------------------------
def get_required_path(option_name):
    # 1. Check for Environment Variable (used by GitHub Actions/Codespaces)
    env_var_name = f"PLATFORMIO_{option_name.upper()}"
    env_val = os.environ.get(env_var_name)
    if env_val:
        return Path(env_val).resolve()
    
    # 2. Check platformio.ini
    path_str = env.GetProjectOption(option_name, "").strip()
    if not path_str:
        raise SystemExit(f"ERROR: '{option_name}' is not set in platformio.ini or environment.")
    
    path = Path(path_str).resolve()
    if not path.exists():
        raise SystemExit(f"ERROR: Path '{path}' for '{option_name}' does not exist.")
    return path

SDK_PATH  = get_required_path("vega_sdk_path")
TOOLS_BIN = get_required_path("vega_tools_path")

# Binary names dynamically adjust for Linux vs Windows
# Note: Official Linux tools usually use 'riscv64-unknown-elf-' prefix
# while some Windows builds use 'riscv64-vega-elf-'. Adjust if necessary.
TOOL_PREFIX = "riscv64-unknown-elf-" if not IS_WINDOWS else "riscv64-vega-elf-"

GCC     = str(TOOLS_BIN / f"{TOOL_PREFIX}gcc{suffix}").replace("\\", "/")
AR      = str(TOOLS_BIN / f"{TOOL_PREFIX}ar{suffix}").replace("\\", "/")
OBJCOPY = str(TOOLS_BIN / f"{TOOL_PREFIX}objcopy{suffix}").replace("\\", "/")

# -----------------------------------------------------------------------
# SDK Directory Mapping
# -----------------------------------------------------------------------
BSP_DIR     = SDK_PATH / "bsp"
INC_DIR     = BSP_DIR / "include"
LD_SCRIPT   = str(BSP_DIR / "common" / "mbl.lds").replace("\\", "/")
CRT_S       = str(BSP_DIR / "common" / "crt.S")
STDLIB_C    = str(BSP_DIR / "common" / "stdlib.c")
RAWFLOAT_C  = str(BSP_DIR / "common" / "rawfloat.c")
DRIVER_SRCS = list((BSP_DIR / "drivers").rglob("*.c"))

INC     = str(INC_DIR).replace("\\", "/")
BSP     = str(BSP_DIR).replace("\\", "/")
SRC_DIR = Path(env.subst("$PROJECT_SRC_DIR")).resolve()
SRC     = str(SRC_DIR).replace("\\", "/")

# -----------------------------------------------------------------------
# Compilation Flags (Enforcing -O0 for timing integrity)
# -----------------------------------------------------------------------
ARCH    = "-march=rv32im -mabi=ilp32 -mcmodel=medany"
INCS    = f"-I{INC} -I{BSP} -I{SRC}"
DEFS    = "-DTHEJAS32"
OPT     = "-O0 -g -fno-builtin-printf -fno-builtin-puts -fno-builtin-memcmp -fno-common -fno-pic -ffunction-sections -fdata-sections"
SDK_STDLIB = f"-include {INC}/stdlib.h"

C_FLAGS   = f"{ARCH} {INCS} {DEFS} {OPT} {SDK_STDLIB}"
LDFLAGS   = f"-nostartfiles -T{LD_SCRIPT} --specs=nano.specs -specs=nosys.specs -Wl,--gc-sections"
LIBS      = f"-L{BSP} -Wl,--start-group -lvega -lc -lgcc -lm -Wl,--end-group"

build_dir = Path(env.subst("$BUILD_DIR")).resolve()
obj_dir   = build_dir / "vega_objs"
obj_dir.mkdir(parents=True, exist_ok=True)

def build_obj(src, obj):
    src_path = Path(src)
    obj_path = Path(obj)
    if not obj_path.exists() or src_path.stat().st_mtime > obj_path.stat().st_mtime:
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        # Use quotes around paths to handle spaces in folder names
        cmd = f'"{GCC}" {C_FLAGS} -c "{str(src)}" -o "{obj}"'
        print(f"[VEGA] Compiling {src_path.name}...")
        subprocess.run(cmd, shell=True, check=True)
    return env.File(str(obj_path))

# -----------------------------------------------------------------------
# Build Steps
# -----------------------------------------------------------------------

# 1. Compile BSP Objects (Drivers + SDK core)
bsp_srcs = DRIVER_SRCS + [Path(STDLIB_C), Path(RAWFLOAT_C)]
bsp_objs = []
for s in bsp_srcs:
    o = obj_dir / "bsp" / f"{s.stem}.o"
    bsp_objs.append(build_obj(s, o))

# Compile Assembly Entry Point (crt.S)
crt_o = obj_dir / "bsp" / "crt.o"
if not Path(crt_o).exists() or Path(CRT_S).stat().st_mtime > Path(crt_o).stat().st_mtime:
    subprocess.run(f'"{GCC}" {ARCH} {INCS} -c "{CRT_S}" -o "{crt_o}"', shell=True, check=True)
bsp_objs.insert(0, env.File(str(crt_o)))

# 2. Compile User Source Objects (src/*.c)
user_srcs = list(SRC_DIR.glob("*.c"))
user_objs = []
for s in user_srcs:
    o = obj_dir / "user" / f"{s.stem}.o"
    user_objs.append(build_obj(s, o))

# 3. Configure PlatformIO Environment
env.Replace(PROGNAME="firmware", PROGSUFFIX=".elf")
env.Append(PIOBUILDFILES=user_objs + bsp_objs)

# Ensure PlatformIO doesn't try to use its own default build logic
env["SRC_FILTER"] = "-<*>"

# Override the Link command to use the RISC-V GCC with our custom flags
env.Replace(
    LINKCOM = f'"{GCC}" {ARCH} {LDFLAGS} -o $TARGET $SOURCES {LIBS}'
)

# 4. Post-Action: Convert ELF to BIN
def objcopy_to_bin(source, target, env):
    elf = str(target[0])
    bin_out = elf.replace(".elf", ".bin")
    subprocess.run(f'"{OBJCOPY}" -O binary "{elf}" "{bin_out}"', shell=True, check=True)
    print(f"[VEGA] Cloud-Ready Binary generated: {bin_out}")

env.AddPostAction("$BUILD_DIR/${PROGNAME}.elf", objcopy_to_bin)
