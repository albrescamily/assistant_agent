FROM pgvector/pgvector:pg17

COPY *.sql *.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/*.sh
