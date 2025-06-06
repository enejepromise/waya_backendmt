FROM python:3.11-bullseye

LABEL maintainer="Eneje Promise"


# Accept PORT as a build argument
ARG PORT=3000

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000

# install necessary packages
RUN apt-get update && \
    apt-get -y install gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# set the working directory
WORKDIR /app

# copy the source code
COPY . /app/

RUN apt-get update && apt-get install -y netcat

# install pip project dependencies
# install pip project dependencies
RUN pip install --upgrade pip setuptools \
    && pip install --trusted-host pypi.python.org -r requirements.txt

    
RUN pip install --upgrade "setuptools<81"

# expose the port using the environment variable
EXPOSE 3000

# Use the gunicorn_config.py as the Gunicorn configuration file
CMD ["gunicorn", "-c", "gunicorn_config.py", "config.wsgi:application"]

