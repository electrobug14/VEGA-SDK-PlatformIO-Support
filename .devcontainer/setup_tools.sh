#!/bin/bash
# Install PlatformIO
pip install -U platformio

# Clone SDK and Tools to a persistent location in the Codespace
cd /home/vscode
git clone https://gitlab.com/riscv-vega/community/vega-sdk.git
git clone https://gitlab.com/riscv-vega/community/vega-tools-rv32.git

# Make binaries executable
chmod +x /home/vscode/vega-tools-rv32/bin/*

# Set Environment Variables for PlatformIO to find them
echo "export PLATFORMIO_VEGA_SDK_PATH=/home/vscode/vega-sdk" >> ~/.bashrc
echo "export PLATFORMIO_VEGA_TOOLS_PATH=/home/vscode/vega-tools-rv32/bin" >> ~/.bashrc
