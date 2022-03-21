# Initialize image
FROM python:3.11.0a6-slim-bullseye
CMD ["mkdir", "/var/www/html"]
COPY . /var/www/html
WORKDIR /var/www/html

# Handles environment variables
ENV PORT 80
ENV DATABASE /var/www/html/database/main.db
ENV PASSWORD false

# Installs Dependencies
RUN apt-get update && apt-get install sqlite3
RUN apt-get install build-essential libffi-dev python-dev -y
RUN pip install -r requirements.txt

# Runs setup scripts and initalizes server
# Need to use sh -c in order to pass env
ENTRYPOINT ["sh", "-c", "(python3 setup_db.py ${DATABASE} && python3 server.py)"]
EXPOSE $PORT