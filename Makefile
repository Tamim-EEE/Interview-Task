.PHONY: test clean migrate

test:
	python manage.py test

migrate:
	python manage.py makemigrations
	python manage.py migrate

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +