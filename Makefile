PROJECT_NAME=genai_plugin_prompt_bridge
PARENT_IMAGE=docker.ci.artifacts.walmart.com/gpa-docker/peopleai/mle_ubuntu:0.8.0
MAINTAINER="People.AI Melody"
MAINTAINER_EMAIL="m0e07zi@walmart.com"

# Project Defaults
PROJECT_WRKDIR=$(PWD)
PROJECT_VERSION=$(shell cat VERSION)
PROJECT_VERSION_BETA=$(shell echo "`cat VERSION`-beta-`date +%Y%m%d%H%M%S`")
TEST_FILE=reports/tests.xml
COVERAGE_FILE=reports/coverage.xml

# Docker Defaults
DOCKER_REGISTRY=docker.ci.artifacts.walmart.com/gpa-docker
DOCKER_NAMESPACE=peopleai
PROJECT_IMAGE_TAGGED_NAME=$(DOCKER_REGISTRY)/$(DOCKER_NAMESPACE)/$(PROJECT_NAME):$(PROJECT_VERSION)
PROJECT_IMAGE_BETA_TAGGED_NAME=$(DOCKER_REGISTRY)/$(DOCKER_NAMESPACE)/$(PROJECT_NAME):$(PROJECT_VERSION_BETA)

# Commands
.DEFAULT_GOAL := help
# Credit https://gist.github.com/klmr/575726c7e05d8780505a
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)";echo;sed -ne"/^## /{h;s/.*//;:d" -e"H;n;s/^## //;td" -e"s/:.*//;G;s/\\n## /---/;s/\\n/ /g;p;}" ${MAKEFILE_LIST}|LC_ALL='C' sort -f|awk -F --- -v n=$$(tput cols) -v i=19 -v a="$$(tput setaf 6)" -v z="$$(tput sgr0)" '{printf"%s%*s%s ",a,-i,$$1,z;m=split($$2,w," ");l=n-i;for(j=1;j<=m;j++){l-=length(w[j])+1;if(l<= 0){l=n-i-length(w[j])-1;printf"\n%*s ",-i," ";}printf"%s ",w[j];}printf"\n";}'|more $(shell test $(shell uname) == Darwin && echo '-Xr')

.PHONY: beta-build-push
## Build/Create the project container
beta-build-push:
	@echo "Building image..."
	@docker build \
	--build-arg MAINTAINER=$(MAINTAINER) \
	--build-arg MAINTAINER_EMAIL=$(MAINTAINER_EMAIL) \
	--build-arg PARENT_IMAGE=$(PARENT_IMAGE) \
	--build-arg PROJECT_NAME=$(PROJECT_NAME) \
	--build-arg PROJECT_VERSION=$(PROJECT_VERSION_BETA) \
	--tag $(PROJECT_IMAGE_BETA_TAGGED_NAME) \
	.
	@echo "Pushing image to artifactory..."
	@docker push $(PROJECT_IMAGE_BETA_TAGGED_NAME)
	@echo "PROJECT_VERSION_BETA=$(PROJECT_VERSION_BETA)"

.PHONY: build
## Build/Create the project container
build: 
	@docker build \
	--build-arg MAINTAINER=$(MAINTAINER) \
	--build-arg MAINTAINER_EMAIL=$(MAINTAINER_EMAIL) \
	--build-arg PARENT_IMAGE=$(PARENT_IMAGE) \
	--build-arg PROJECT_NAME=$(PROJECT_NAME) \
	--build-arg PROJECT_VERSION=$(PROJECT_VERSION) \
	--tag $(PROJECT_IMAGE_TAGGED_NAME) \
	.

.PHONY: push
## Push image to artifactory
push:
	@docker push $(PROJECT_IMAGE_TAGGED_NAME)

.PHONY: run
## Run the project container with bash command
run: build
	@docker run \
	-it \
	--env-file ./local.env \
	-p 8000:8000 \
	$(PROJECT_IMAGE_TAGGED_NAME)

.PHONY: bash
## Run the project container with bash command
bash: build
	@docker run \
	-it \
	-p 8000:8000 \
	--entrypoint /bin/bash \
	$(PROJECT_IMAGE_TAGGED_NAME)

.PHONY: test
## run `test` against the project
test:
	@python -m pip install -i https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/gpa-pypi/simple -r requirements.txt mock --upgrade
	@python -m pytest -s -vv tests/ --cov=. --cov-report html:reports/html --cov-report xml:reports/coverage.xml --junitxml=reports/tests.xml
	-@python -m coverage xml -i

.PHONY: test_looper
## run `test` against the project
test_looper: test
	@echo $(COVERAGE_FILE)
	@sed -i "s|/mnt/workspace|.|g" reports/coverage.xml
	@sed -i "s|/mnt/workspace|.|g" $(COVERAGE_FILE)
ifneq ("$(wildcard $(COVERAGE_FILE))","")
	@echo "coverage.xml found"
	@sed -i 's|/mnt/workspace|.|g' reports/coverage.xml
else
	@echo "coverage.xml does not exist"
endif

.PHONY: black
## run `black` against the project
black:
	@black -S src/$(PROJECT_NAME)

.PHONY: lint
## Run `pylint` against the project
lint:
	@pylint src/$(PROJECT_NAME)

.PHONY: docker-rm-none
## Remove images named <none>
docker-rm-none:
	@docker rmi -f $(docker images --filter "dangling=true" -q --no-trunc)

## Basic env check
env-check-flow:
	@env
	@python --version
	@python3 --version
	@pip --version
	@pip3 --version
	@twine --version
	@git --version
	@cat ~/.bashrc
	@pwd
	@ls

.PHONY: version
#Return version to looper
version:
	@echo $(PROJECT_VERSION)
