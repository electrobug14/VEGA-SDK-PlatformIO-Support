# System Integration Guide: THEJAS32 RISC-V on PlatformIO

![Baremetal RISC-V in VS Code](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/1.jpg)

> *Unlocking the C-DAC Aries V3 with PlatformIO — a transparent wrapper for the VEGA ET1031 toolchain.*

## Table of Contents

1. [Project Scope and Integration Objectives](#1-project-scope-and-integration-objectives)
2. [Cross-Platform Environment Architecture](#2-cross-platform-environment-architecture)
3. [Build System Orchestration via Python Extra Scripts](#3-build-system-orchestration-via-python-extra-scripts)
4. [Compiler Optimization and Timing Integrity](#4-compiler-optimization-and-timing-integrity)
5. [Internal XMODEM Upload Mechanisms](#5-internal-xmodem-upload-mechanisms)
6. [Application Integration Case Study: SSD1306 OLED](#6-application-integration-case-study-ssd1306-oled)
7. [Integration Summary and Best Practices](#7-integration-summary-and-best-practices)

---

## 1. Project Scope and Integration Objectives

![The Friction of Legacy IDEs](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/2.jpg)

The strategic objective of this engineering initiative is to bridge the **C-DAC Aries V3 (THEJAS32)** hardware—powered by the **VEGA ET1031 RISC-V core**—with the PlatformIO ecosystem. Migrating from legacy Eclipse-based IDEs and fragile, manually maintained Makefiles toward a modern, unified workflow in VS Code is not merely a convenience; it is a mandate for developer productivity and firmware reliability. By integrating the manufacturer's specialized toolchain into a robust IDE, we eliminate "environment drift" and provide a repeatable build-and-deploy cycle.

The integration mandate requires the creation of a clean, baremetal development environment. This involves intercepting the PlatformIO build lifecycle to inject the VEGA SDK, custom build logic, and proprietary XMODEM-based upload protocols. The result is a unified VS Code experience where the complexities of the underlying RISC-V toolchain are abstracted without sacrificing low-level control.

### Prerequisites

Successful deployment of this integration on a Windows host requires the following components:

| Component | Description |
|---|---|
| **VS Code & PlatformIO IDE Extension** | The primary orchestration and editing environment |
| **VEGA SDK** | The source-level Board Support Package (BSP) and drivers |
| **VEGA Toolchain for Windows** | The specific cross-compiler binaries (e.g., `riscv64-vega-elf-gcc`) |
| **VEGA Upload Tools** | The directory containing the custom XMODEM flasher utility (`flasher.bat`) |

---

## 2. Cross-Platform Environment Architecture

![The Paradigm Shift Matrix](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/3.jpg)

A significant challenge in supporting non-standard RISC-V architectures within a generic IDE is the "Native" platform assumption. To resolve this, a strategic **"architectural shell"** has been implemented using the PlatformIO `native` platform. This approach allows hosting a completely custom toolchain while manually overriding the internal SCons build graph, preventing the system from defaulting to host-system compilers like MSVC or MinGW.

![The Transparent Wrapper Philosophy](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/4.jpg)

The integration is centered in `platformio.ini`. The following keys map the required environmental variables to the integration logic:

| Configuration Key | Functional Role |
|---|---|
| `vega_sdk_path` | Absolute path to the source-level VEGA SDK and BSP |
| `vega_tools_path` | Absolute path to the `riscv64-vega-elf` binaries (GCC, AR, OBJCOPY) |
| `vega_flasher_dir` | The directory used by `${this.vega_flasher_dir}` for interpolation in the `UPLOADCMD` |

![Anatomy of the Hijack: platformio.ini](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/5.jpg)

The hardware abstraction is solidified in the `aries_v3.json` board definition. By explicitly defining the CPU as `vega-et1031` and the MCU as `thejas32`, the necessary context is provided for the custom scripts.

> **Note:** The `f_cpu` value of `100000000L` (100 MHz) in the board JSON is the **single source of truth** that aligns with the `SYSTEM_FREQUENCY` requirements found in the peripheral drivers.

---

## 3. Build System Orchestration via Python Extra Scripts

![Intercepting the Build Signal](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/6.jpg)

The use of `extra_scripts` is essential for intercepting the PlatformIO lifecycle. These scripts act as the "bridge" between the static SDK and the dynamic build process, allowing overrides of toolchain naming conventions and memory mapping.

### Pre-Build Logic (`build_vega.py`)

![The build_vega.py Compilation Pipeline](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/7.jpg)

This script performs the heavy lifting of path resolution and toolchain selection.

> **Windows Compatibility:** A critical best practice implemented here is the use of `Path().resolve()` followed by `.replace("\\", "/")`, ensuring the toolchain handles file paths correctly regardless of the shell environment.

![The Compilation Recipe (build_vega.py)](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/8.jpg)

The script manages a **three-stage compilation sequence**:

1. **BSP Object Generation** — Compiling driver sources and SDK essentials like `stdlib.c` and `rawfloat.c`
2. **User Object Compilation** — Processing application code within the `src/` directory
3. **Linker Execution** — Utilizing the `mbl.lds` script to define the address space mapping

To prevent the native PlatformIO compiler from interfering, a source filtering strategy is enforced:

```ini
build_src_filter = -<*>
```

> **Important:** This instruction ensures the host compiler does not attempt to compile RISC-V code, leaving all logic to the intercepted `build_vega.py` routine.

Finally, a post-action routine utilizes `objcopy` to transform the `.elf` binary into a flashable `.bin` format.

---

## 4. Compiler Optimization and Timing Integrity

![The Optimization Trap](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/9.jpg)

In baremetal development, aggressive compiler optimization is often the enemy of timing integrity. Standard IDE defaults like `-O2` can be catastrophic for the THEJAS32 SDK, as the compiler may "dead-code eliminate" software delay loops (like `udelay()`) that lack the `volatile` keyword or reorder critical I/O register writes.

To ensure stability, `build_vega.py` explicitly enforces **`-O0` (no optimization)**, paired with several mandatory RISC-V ISA and memory model flags:

| Flag | Purpose |
|---|---|
| `-march=rv32im -mabi=ilp32` | Ensures compiler produces instructions and calling conventions compatible with the VEGA ET1031 core |
| `-mcmodel=medany` | Required for RISC-V medium-any memory modeling to handle address resolution |
| `-fno-pic -fno-common` | Prevents generation of position-independent code and ensures global variables are handled predictably in a baremetal context |
| `-nostartfiles` | Provides manual control over the entry point, allowing use of the custom `crt.S` Assembly Entry Point for stack pointer initialization |
| `-fno-builtin-printf` | Prevents the compiler from replacing simple `printf` calls with standard library versions that may not exist in the limited VEGA environment |
| `--specs=nano.specs -specs=nosys.specs` | Linker flags that prevent inclusion of a full, OS-dependent C library, keeping the binary footprint lean |

![RISC-V Memory Models & Libraries](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/10.jpg)

These constraints ensure timing and pointer integrity across all build cycles.

---

## 5. Internal XMODEM Upload Mechanisms

![The Flasher Override (upload_vega.py)](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/11.jpg)

Deploying code to the Aries V3 represents the "last mile" of the integration. Because the THEJAS32 uses a manufacturer-specific bootloader rather than standard JTAG, the `UPLOADCMD` environment variable must be overridden via `upload_vega.py`.

### Orchestrating the Flasher

The script intercepts the native PlatformIO "upload" target—which would otherwise try to execute the binary as a Windows process—and redirects it to the proprietary `flasher.bat`. This utility utilizes the **XMODEM protocol** for serial data transfer.

### Operational Requirements

![Build and Upload UI](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/12.jpg)

- **Parameter Passing** — The script dynamically passes the `upload_port` and the path to the `firmware.elf` (interpolated via `$BUILD_DIR`)
- **Serial Port Exclusivity** — Due to the nature of the XMODEM transfer, it is a critical prerequisite that **no other serial monitors** (e.g., TeraTerm or PuTTY) occupy the COM port during the flashing process

> ⚠️ **Warning:** Failing to close active serial monitors before flashing will cause the XMODEM transfer to fail.

---

## 6. Application Integration Case Study: SSD1306 OLED

![Hardware Validation: SSD1306 OLED](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/13.jpg)

To verify the full integration stack, a hardware-in-the-loop test was conducted using an **SSD1306 OLED display**. This verifies everything from I2C driver timing to memory-mapped asset handling.

### The I2C Data Pipeline

![The I2C Data Pipeline](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/14.jpg)

### Peripheral Initialization and Timing

![Application Layer: Clean Baremetal C](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/15.jpg)

Initial setup requires calling:

```c
i2c_configure(I2C_0, SYSTEM_FREQUENCY, 100000);
ssd1306_begin(SSD1306_SWITCHCAPVCC, 0x78);

char *text = "VEGA microprocessors";
ssd1306_drawString(text);
ssd1306_display();
```

Here, `SYSTEM_FREQUENCY` is derived from the 100 MHz clock defined in the board JSON. This explicit definition ensures the I2C clock (100 kHz) is generated accurately by the hardware.

### Memory Management of Assets

This case study highlights the manual memory management required in baremetal environments. Graphical assets like `buffer_logo` (found in `ssd1306.c`) are raw arrays stored in the RISC-V memory space.

To render these, the system uses `fill_logo()`—a manual routine that copies the static logo array into the active display buffer. This process relies on the custom `stdlib.c` provided by the SDK rather than standard `libc`, ensuring that memory-intensive operations like `memset` function within the silicon's specific constraints.

---

## 7. Integration Summary and Best Practices

The PlatformIO/Aries V3 bridge provides a robust, professional-grade development environment that supersedes legacy tools. By utilizing toolchain interception and strict optimization controls, a reliable path for RISC-V development is established.

### Key Integration Takeaways

1. **Mandatory `-O0` Optimization** — Non-negotiable for preserving timing loops and pointer-based data arrays
2. **ISA-Specific Flag Enforcement** — The inclusion of `-march=rv32im` and `-mabi=ilp32` is critical for core compatibility
3. **Cross-Platform Path Management** — Using Python's `Path().resolve()` and separator replacement is vital for Windows-based toolchain stability

### Quick-Start Blueprint

![The Quick-Start Blueprint](https://github.com/nishit0072e/VEGA-SDK-PlatformIO-Support/blob/main/docs/images/16.jpg)

### Operational Checklist

| Step | Action | Tool / Command |
|---|---|---|
| 1. Configuration | Edit `platformio.ini` — insert absolute paths to your local VEGA SDK, Tools, and Flasher directory | Text Editor |
| 2. Hardware | Plug the Aries V3 UART/Debug USB into the PC — identify the COM port (e.g., `COM3`) in Windows Device Manager | Windows Device Manager |
| 3. Build & Flash | Ensure PuTTY/TeraTerm is closed — click the VS Code PlatformIO `✓` (Build) and `→` (Upload) icons | `pio run` / `pio run --target upload --upload-port COM3` |
