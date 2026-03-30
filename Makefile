# Root Makefile for multi-project builds
SDK_PATH ?= $(shell pwd)/vega-sdk

# Find all folders in src/ that have a main.c file
PROJECT_DIRS := $(shell find src -maxdepth 2 -name 'main.c' -exec dirname {} \;)

.PHONY: all clean $(PROJECT_DIRS)

all: $(PROJECT_DIRS)

$(PROJECT_DIRS):
	@echo "--- Building $@ ---"
	$(MAKE) -C $@ SDK_PATH=$(SDK_PATH)

clean:
	@for dir in $(PROJECT_DIRS); do \
		$(MAKE) -C $$dir clean; \
	done
