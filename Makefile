COPY_FILES = $(patsubst src/%,public/%,$(wildcard src/*) $(wildcard src/*/*))

all: src/demo_data.js $(COPY_FILES)

# The demo data is generated from public_demo.html; regenerate it whenever the
# export or the config in build_demo_data.py changes. Order-only prerequisite
# below so this always runs before anything is copied into public/.
src/demo_data.js: src/build_demo_data.py src/public_demo.html
	python3 src/build_demo_data.py

$(COPY_FILES): | src/demo_data.js

public/%: src/%
	echo $@
	cp -r -f -v -T $< $@

deploy: src/demo_data.js
	rsync -a --info=name src/ public/ --exclude=.git/*
