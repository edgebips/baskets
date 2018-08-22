#!/usr/bin/env make

lint:
	DISABLE_AUTOIMPORTS=1 python3 -m pylint --rcfile=$(PWD)/etc/pylintrc baskets
