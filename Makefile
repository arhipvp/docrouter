.PHONY: build-frontend run up

build-frontend:
	npx tsc

run:
	python main.py

up:
	docker compose up --build
