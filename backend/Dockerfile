FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy>=2.0 psycopg2-binary alembic pydantic-settings python-jose[cryptography] bcrypt redis rq pyjwt httpx
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
