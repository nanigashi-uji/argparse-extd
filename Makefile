PYTHON ?= python3

all: README.rst sdist bdist_wheel

README.rst: README.md
	pandoc --from markdown --to rst $^ -o $@

clean:
	rm -rf argparse_extd.egg-info/* dist/* build/* *~ argparse_extd/*~ example/*~

distclean: clean 
	rm -rf argparse_extd.egg-info dist build README.rst

sdist: README.rst
	$(PYTHON) setup.py $@

bdist_wheel: README.rst
	$(PYTHON) setup.py $@

test_upload: sdist bdist_wheel
	twine upload --verbose --repository pypitest dist/*

upload: sdist bdist_wheel
	twine upload --verbose dist/*
