#!/usr/bin/env make -f

PY_SRC = $(wildcard *.py)
TARGETS = $(addprefix export/, $(notdir $(PY_SRC:.py=)))

all: $(TARGETS)

export/%: %.py
	python $< export $@

clean:
	rm -f export/*.{stl,step}
