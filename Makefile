#!/usr/bin/env make

lint:
	DISABLE_AUTOIMPORTS=1 pylint --rcfile=$(PWD)/etc/pylintrc baskets
