FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY par/ par/
RUN pip install --no-cache-dir .

FROM python:3.12-slim

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/par /usr/local/bin/par

WORKDIR /rules
ENTRYPOINT ["par"]
CMD ["--help"]
