up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f api

test:
	# You would run pytest here if you write the tests in tests/
	# docker compose run api pytest