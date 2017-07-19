init:
	pip install -r requirements.txt

doc-update:
	sphinx-apidoc -o docs hpcbench

test:
	nosetests tests
