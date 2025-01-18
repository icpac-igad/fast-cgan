# --------- requirements ---------
# ARG PYTHON_VERSION=3.11
# FROM python:${PYTHON_VERSION}-slim AS builder

# WORKDIR /tmp

# RUN pip install poetry poetry-plugin-export

# COPY ./pyproject.toml ./poetry.lock* ./README.md /tmp/

# RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


# --------- final image build ---------
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS runner

ARG WORK_HOME=/opt/app
ARG USER_NAME=cgan
ARG USER_ID=1000
ARG GROUP_ID=1000

RUN apt-get update -y && \
    apt-get install libeccodes-dev git -y --no-install-recommends && \
    mkdir -p ${WORK_HOME}/.local/bin

RUN groupadd --gid ${GROUP_ID} ${USER_NAME} && \
    useradd --home-dir ${WORK_HOME} --uid ${USER_ID} --gid ${GROUP_ID} ${USER_NAME} && \
    chown -Rf ${USER_NAME}:${USER_NAME} ${WORK_HOME}

USER ${USER_NAME}
WORKDIR ${WORK_HOME}

# COPY --from=builder /tmp/requirements.txt ${WORK_HOME}/requirements.txt
COPY --chown=${USER_ID}:root README.md pyproject.toml poetry.lock ${WORK_HOME}/
COPY --chown=${USER_NAME}:root ./fastcgan ${WORK_HOME}/fastcgan
ENV PATH=${WORK_HOME}/.local/bin:${PATH}
RUN pip install --no-cache-dir --upgrade -e .

# COPY --chown=${USER_ID}:root ./fastcgan  ${WORK_HOME}/fastcgan

CMD ["uvicorn", "fastcgan.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
