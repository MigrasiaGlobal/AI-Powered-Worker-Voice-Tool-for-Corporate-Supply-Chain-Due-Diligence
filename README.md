# PoBot - Supply Chain Legal Assistant

PoBot is a Django-based chatbot application designed to assist workers in identifying and reporting policy violations in supply chains. The application includes a chatbot interface for collecting information about incidents and a dashboard for viewing and analyzing reported cases.

## Features

- Interactive chatbot interface for collecting incident information
- Case type identification based on user input
- Automatic detection of factory names and buyer companies
- Policy violation analysis based on company policies
- Dashboard for viewing all chat sessions and policy violations
- Detailed session view with conversation history and violation reports

## Project Structure

- `chatbot/`: Django app containing the chatbot and dashboard functionality
- `pobot_project/`: Django project settings and configuration
- `templates/`: HTML templates for the web interface
- `static/`: CSS and JavaScript files for the frontend

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Apply migrations: `python manage.py migrate`
4. Create a superuser: `python manage.py createsuperuser`
5. Run the development server: `python manage.py runserver`

## Usage

1. Access the chatbot at `https://pobotsupplychain.azurewebsites.net/`
2. Start a conversation with PoBot
3. Provide information about your incident
4. View the dashboard at `https://pobotsupplychain.azurewebsites.net/dashboard/`
## Requirements

- Python 3.8+
- Django 5.0+
- Ollama for LLM integration
- NetworkX for graph-based conversation flow
- Pandas for data processing

