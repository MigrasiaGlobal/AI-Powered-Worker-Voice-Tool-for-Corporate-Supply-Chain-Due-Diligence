FROM python:3.11
WORKDIR /pobotapp


# Install dependencies for LibreOffice
RUN apt-get update && apt-get install -y \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-common \
    fonts-dejavu-core \
    python3-pip \
    python3-uno \
    curl \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


RUN python -c "from langchain.embeddings import SentenceTransformerEmbeddings; SentenceTransformerEmbeddings(model_name='all-MiniLM-L6-v2')"

COPY pobot_project/ ./pobot_project/
COPY chatbot/ ./chatbot/
COPY staticfiles/ ./staticfiles/
COPY static/ ./static/
COPY templates/ ./templates/
COPY db.sqlite3 ./db.sqlite3
COPY manage.py ./manage.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN python manage.py collectstatic --noinput
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
