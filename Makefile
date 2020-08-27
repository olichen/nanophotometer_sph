build:
	pyinstaller --onefile --name nanophotometer_sph nanophotometer_sph.py

lint:
	flake8

install-dev:
	pip install pipenv
	pipenv install --dev

run:
	python nanophotometer_sph.py
