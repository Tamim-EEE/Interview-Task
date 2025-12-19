.PHONY: test clean chaos_test migrate

test:
	python manage.py test

chaos_test:
	python scripts/chaos_test.py

migrate:
	python manage.py makemigrations
	python manage.py migrate

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +