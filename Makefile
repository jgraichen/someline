#!/usr/bin/env make -f
# vim: ft=makefile

FCS = $(shell find . -type f -name '*.FCStd' -not -path '*/parts/*' | sort)

EXPORT_STL = $(join $(addsuffix export/, $(dir $(FCS))), $(notdir $(FCS:.FCStd=.stl)))
EXPORT_STEP = $(join $(addsuffix export/, $(dir $(FCS))), $(notdir $(FCS:.FCStd=.step)))

BIN := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))bin/
export PATH := $(BIN):$(PATH)

all: stl step
stl: $(EXPORT_STL)
step: $(EXPORT_STEP)

list:
	@echo $(FCS) | xargs -n1 echo

export/%.stl &: %.FCStd
	./bin/export.py "$^" --format=stl

export/%.step: %.FCStd
	./bin/export.py "$^" --format=step

clean:
	rm -f export/*.{stl,step}
