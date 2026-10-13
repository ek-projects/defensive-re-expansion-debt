PYTHON ?= python3
VENDOR := vendor/skillcorner-opendata

.PHONY: install vendor data data-public-all validate validate-public-all epv focused focused-public-all shot-audit case bodypose-data bodypose test all clean-derived

install:
	$(PYTHON) -m pip install -e '.[dev]'

vendor:
	@test -d $(VENDOR)/.git || GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --filter=blob:none https://github.com/SkillCorner/opendata.git $(VENDOR)

data: vendor
	PYTHONPATH=src $(PYTHON) scripts/fetch_dataset.py

data-public-all: vendor
	PYTHONPATH=src $(PYTHON) scripts/fetch_dataset.py --all-public-matches

validate:
	PYTHONPATH=src $(PYTHON) scripts/batch_validate.py

validate-public-all:
	PYTHONPATH=src $(PYTHON) scripts/batch_validate.py --all-public-matches

epv:
	PYTHONPATH=src $(PYTHON) scripts/validate_epv.py

focused:
	PYTHONPATH=src $(PYTHON) scripts/focused_analysis.py

shot-audit: focused

focused-public-all:
	PYTHONPATH=src $(PYTHON) scripts/focused_analysis.py --all-public-matches

case:
	PYTHONPATH=src $(PYTHON) scripts/case_study.py

bodypose-data:
	$(PYTHON) scripts/fetch_bodypose.py

bodypose: bodypose-data
	PYTHONPATH=src $(PYTHON) scripts/bodypose_validate.py

test:
	PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest -q -p no:cacheprovider

all: data validate epv case test

clean-derived:
	rm -rf data/processed outputs
