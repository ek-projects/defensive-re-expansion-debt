PYTHON ?= python3
VENDOR := vendor/skillcorner-opendata

.PHONY: install vendor data validate epv robustness adversarial hardening focused shot-audit case bodypose-data bodypose test release-audit all clean-derived

install:
	$(PYTHON) -m pip install -e '.[dev]'

vendor:
	@test -d $(VENDOR)/.git || GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --filter=blob:none https://github.com/SkillCorner/opendata.git $(VENDOR)

data: vendor
	PYTHONPATH=src $(PYTHON) scripts/fetch_dataset.py

validate: data
	PYTHONPATH=src $(PYTHON) scripts/batch_validate.py

epv: validate
	PYTHONPATH=src $(PYTHON) scripts/validate_epv.py

robustness: validate
	PYTHONPATH=src $(PYTHON) scripts/robustness_epv.py

focused: validate
	PYTHONPATH=src $(PYTHON) scripts/focused_analysis.py

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
