PY ?= python3
export PYTHONPATH := src

.PHONY: test quick suite probe matrix clean
test:
	$(PY) -m unittest discover -s tests -v
quick:
	$(PY) -m cxltier suite --quick --out results/quick
suite:
	$(PY) -m cxltier suite --out results/full
probe:
	$(PY) -m cxltier probe
matrix:
	$(PY) -m cxltier matrix
clean:
	rm -rf results/quick results/full
