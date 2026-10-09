PYTHON ?= python3
PRODUCT ?= 645
SEED ?= 42
TICKETS ?= 5
WINDOW ?= 60

.DEFAULT_GOAL := help
.PHONY: help crawl predict stats backtest test

help:
	@echo "make crawl     Update all lottery CSV files"
	@echo "make predict   Generate tickets (PRODUCT=645 SEED=42 TICKETS=5 WINDOW=60)"
	@echo "make stats     Show historical statistics (PRODUCT=645 WINDOW=60)"
	@echo "make backtest  Run historical backtest (PRODUCT=645 WINDOW=60)"
	@echo "make test      Run all tests"

crawl:
	$(PYTHON) crawl.py

predict:
	$(PYTHON) main.py predict --data databases/$(PRODUCT).csv --product $(PRODUCT) --seed $(SEED) --tickets $(TICKETS) --window $(WINDOW)

stats:
	$(PYTHON) main.py stats --data databases/$(PRODUCT).csv --product $(PRODUCT) --window $(WINDOW)

backtest:
	$(PYTHON) main.py backtest --data databases/$(PRODUCT).csv --product $(PRODUCT) --window $(WINDOW)

test:
	$(PYTHON) -m unittest discover -s tests -v
