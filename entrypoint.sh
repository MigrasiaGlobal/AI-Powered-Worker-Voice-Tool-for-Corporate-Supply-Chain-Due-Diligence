#!/bin/bash

# Only run migrations if database doesn't exist or needs updates
# This preserves existing data while allowing for schema updates
python manage.py migrate --run-syncdb

# Start the Django development server
python manage.py runserver 0.0.0.0:8000 --noreload
