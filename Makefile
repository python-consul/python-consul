VERSION = $(shell git describe --tags --match '[0-9]*.[0-9]' --abbrev=0)
REV = $(shell git rev-list $(VERSION)..HEAD | wc -l)

update_version:
	echo "Version $(VERSION) and Rev $(REV)"; echo '__version__ = '\''$(VERSION).$(REV)'\''' > consul/consul_version.py

build: update_version
	python setup.py sdist --formats=zip

init:
	pip install -r requirements.txt && pip install -r requirements-devel.txt

test:
	nosetests tests
