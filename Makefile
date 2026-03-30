# Root Wrapper Makefile
SDK_PATH ?= /home/vscode/vega-sdk
TOOLS_PATH ?= /home/vscode/vega-tools-rv32/bin
export PATH := $(TOOLS_PATH):$(PATH)

# Find all subdirectories in src that have a main.c
PROJECTS := $(shell find src -maxdepth 2 -name 'main.c' -exec dirname {} \;)

.PHONY: all clean $(PROJECTS)

all: $(PROJECTS)

$(PROJECTS):
	@echo "Building project in $@..."
	$(MAKE) -C $@ SDK_PATH=$(SDK_PATH)

clean:
	@for dir in $(PROJECTS); do \
		$(MAKE) -C $$dir clean; \
	done
