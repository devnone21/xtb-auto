FROM python:3.10 as builder

COPY requirements.txt ./
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels websockets

# final stage
FROM python:3.10-slim

WORKDIR /usr/src/app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . .

CMD [ "python", "-u", "./app.py" ]
