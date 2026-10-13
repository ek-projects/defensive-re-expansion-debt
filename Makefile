PYTHON ?= python3
VENDOR := vendor/skillcorner-opendata

.PHONY: install vendor data data-competition-20 validate validate-competition-20 epv robustness adversarial hardening focused focused-competition-20 shot-audit case bodypose-data bodypose test release-audit all clean-derived

install:
	$(PYTHON) -m pip install -e '.[dev]'

vendor:
	@test -d $(VENDOR)/.git || GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --filter=blob:none https://github.com/SkillCorner/opendata.git $(VENDOR)

data: vendor
	PYTHONPATH=src $(PYTHON) scripts/fetch_dataset.py

data-competition-20: vendor
	PYTHONPATH=src $(PYTHON) scripts/fetch_dataset.py --all-competition-matches

validate: data
	PYTHONPATH=src $(PYTHON) scripts/batch_validate.py

validate-competition-20: data-competition-20
	PYTHONPATH=src $(PYTHON) scripts/batch_validate.py --all-competition-matches

epv: validate
	PYTHONPATH=src $(PYTHON) scripts/validate_epv.py

robustness: validate
	PYTHONPATH=src $(PYTHON) scripts/robustness_epv.py

focused: validate
	PYTHONPATH=src $(PYTHON) scripts/focused_analysis.py

focused-competition-20: validate-competition-20
	PYTHONPATH=src $(PYTHON) scripts/focused_analysis.py --all-competition-matches

shot-audit: focused

case: focused
	PYTHONPATH=src $(PYTHON) scripts/case_study.py

bodypose-data:
	$(PYTHON) scripts/fetch_bodypose.py

bodypose: bodypose-data
	PYTHONPATH=src $(PYTHON) scripts/bodypose_validate.py

test:
	PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest -q -p no:cacheprovider

release-audit:
	$(PYTHON) scripts/release_audit.py

all: data validate epv case test

clean-derived:
	rm -rf data/processed outputs

adversarial: focused
	PYTHONPATH=src:scripts $(PYTHON) scripts/adversarial_epv_audit.py

hardening: robustness adversarial test
