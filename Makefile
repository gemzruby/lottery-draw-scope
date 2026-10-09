PYTHON ?= python3
PRODUCT ?= 645
SEED ?= 42
TICKETS ?= 5
WINDOW ?= 60
SAMPLES ?= 1000
STRATEGY ?= predict
BACKTEST_SEED ?= 0
WORKERS ?= 2
ROUND_SEED ?=
RUNS ?= 10
RESUME ?=
STAGES ?= 10 30 100
RECOMMENDATIONS ?= 2

.DEFAULT_GOAL := help
.PHONY: help crawl predict simulate stats backtest evaluate round stability test

help:
	@echo "make crawl     Update all lottery CSV files"
	@echo "make predict   Generate tickets (PRODUCT=645 SEED=42 TICKETS=5 WINDOW=60)"
	@echo "make simulate  Rank numbers from sampled tickets (PRODUCT=645 SEED=42 SAMPLES=1000 WINDOW=60)"
	@echo "make stats     Show historical statistics (PRODUCT=645 WINDOW=60)"
	@echo "make backtest  Run historical backtest (PRODUCT=645 WINDOW=60)"
	@echo "make round     Run a round (PRODUCT=645 RUNS=10 SAMPLES=1000 WORKERS=2)"
	@echo "make stability Compare nested checkpoints (PRODUCT=645 STAGES='10 30 100' RECOMMENDATIONS=2)"
	@echo "make evaluate  Alias for make round"
	@echo "make test      Run all tests"

crawl:
	$(PYTHON) crawl.py

predict:
	$(PYTHON) main.py predict --data databases/$(PRODUCT).csv --product $(PRODUCT) --seed $(SEED) --tickets $(TICKETS) --window $(WINDOW)

stats:
	$(PYTHON) main.py stats --data databases/$(PRODUCT).csv --product $(PRODUCT) --window $(WINDOW)

simulate:
	$(PYTHON) main.py simulate --data databases/$(PRODUCT).csv --product $(PRODUCT) --seed $(SEED) --samples $(SAMPLES) --window $(WINDOW)

backtest:
	$(PYTHON) main.py backtest --data databases/$(PRODUCT).csv --product $(PRODUCT) --window $(WINDOW) --strategy $(STRATEGY) --samples $(SAMPLES) --seed $(BACKTEST_SEED)

round:
	$(PYTHON) run_round.py --product $(PRODUCT) $(if $(ROUND_SEED),--seed $(ROUND_SEED),) --samples $(SAMPLES) --workers $(WORKERS) --runs $(RUNS) --recommendations $(RECOMMENDATIONS) $(if $(RESUME),--resume $(RESUME),)

stability:
	$(PYTHON) -m experiments.stability --product $(PRODUCT) --stages $(STAGES) --recommendations $(RECOMMENDATIONS) $(if $(ROUND_SEED),--seed $(ROUND_SEED),) --samples $(SAMPLES) --workers $(WORKERS) $(if $(RESUME),--resume $(RESUME),)

evaluate: round

test:
	$(PYTHON) -m unittest discover -s tests -v
