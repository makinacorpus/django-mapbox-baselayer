-include Makefile.perso.mk

###########################
#          colors         #
###########################
PRINT_COLOR = printf
COLOR_SUCCESS = \033[1;32m
COLOR_DEBUG = \033[36m
COLOR_RESET = \033[0m

.PHONY: serve
serve:
	@$(PRINT_COLOR) "$(COLOR_SUCCESS) \n### Start server ###\n $(COLOR_RESET)\n"
	$(docker_compose) up

###########################
#          Lint           #
###########################
.PHONY: format
format:
	ruff format mapbox_baselayer test_mapbox_baselayer

.PHONY: lint
lint:
	ruff check --fix mapbox_baselayer test_mapbox_baselayer

.PHONY: force_lint
force_lint:
	ruff check --fix --unsafe-fixes mapbox_baselayer test_mapbox_baselayer

.PHONY: quality
quality: lint format

###########################
#          Test           #
###########################

verbose_level ?= 1
report ?= report -m
.PHONY: coverage
coverage:
	@$(PRINT_COLOR) "$(COLOR_SUCCESS) ### Start coverage ### $(COLOR_RESET)\n"
	coverage run --parallel-mode --concurrency=multiprocessing ./manage.py test $(test_name) --parallel -v $(verbose_level) || true
	coverage combine && coverage $(report)
	coverage xml -o coverage.xml
	rm .coverage || true

verbose_level ?= 1
.PHONY: test
test:
	@$(PRINT_COLOR) "$(COLOR_SUCCESS) ### Start tests ### $(COLOR_RESET)\n"
	./manage.py test $(test_name) --parallel -v $(verbose_level)

messages_python:
	./manage.py makemessages -a --no-location --no-obsolete --no-wrap

messages: messages_python
