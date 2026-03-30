# Target name
TARGET = firmware

# Include all .c files in this specific directory
SRCS = $(wildcard *.c)
OBJS = $(SRCS:.c=.o)

# Pull in the official SDK configuration
# This is what makes it work exactly like the GitLab repo
include $(SDK_PATH)/bsp/common/common.mk

.PHONY: all
all: $(TARGET).bin $(TARGET).elf $(TARGET).hex
