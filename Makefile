init:
	pip install tox

doc-update:
	sphinx-apidoc -o docs hpcbench

test:
	tox
	flake8 hpcbench
	pylint hpcbench
