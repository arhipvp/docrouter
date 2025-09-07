.PHONY: build-frontend run up

build-frontend:
	npx tsc

run:
	python -m web_app.server

up:
	docker compose up --build
