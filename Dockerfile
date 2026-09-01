FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /code

# No system packages (gcc/libpq-dev) needed: requirements.txt uses
# psycopg2-binary, which ships a precompiled wheel with libpq bundled
# in — that's the whole point of the "-binary" variant. Dropping the
# apt-get step entirely removes the flaky Debian-mirror dependency
# that was timing out the build.
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /code/