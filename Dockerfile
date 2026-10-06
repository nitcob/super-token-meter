# Super Token Meter — optional container image.
# The runtime is Python standard library only, so there is nothing to pip-install:
# we just copy the source and run it. See compose.yaml for the recommended wiring.
FROM python:3.12-slim

WORKDIR /app
COPY super_token_meter ./super_token_meter
COPY examples ./examples

ENV STM_DATA_DIR=/data
EXPOSE 8722

# Collect from a mounted ~/.claude (see compose.yaml), then serve. It binds 0.0.0.0 INSIDE
# the container; keep it localhost-only by mapping the port to 127.0.0.1 on the host.
CMD ["python", "-m", "super_token_meter", "serve", "--host", "0.0.0.0", "--port", "8722", "--no-browser"]
