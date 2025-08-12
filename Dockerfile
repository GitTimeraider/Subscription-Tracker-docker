FROM python:3.13-slim

WORKDIR /app

# Install gosu for safe privilege dropping
RUN apt-get update \
	&& apt-get install -y --no-install-recommends gosu \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Entrypoint will create/update user/group according to PUID/PGID
RUN chmod +x /app/docker-entrypoint.sh

ENV FLASK_APP=run.py \
	PUID=1000 \
	PGID=1000

EXPOSE 5000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]
