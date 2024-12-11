# --------- requirements ---------

FROM python:3.13 AS requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* ./README.md /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


# --------- final image build ---------
FROM python:3.13 AS runner

RUN apt-get update -y && apt-get install libeccodes-dev -y --no-install-recommends

WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./fastcgan /code/fastcgan

CMD ["uvicorn", "fastcgan.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
