# ARG PYTHON_VERSION=3.10
# FROM python:${PYTHON_VERSION}-slim AS builder

# ARG GAN_REPO=https://github.com/jaysnm/ensemble-cgan.git
# ARG GAN_BRANCH=main

# WORKDIR /tmp
# RUN apt-get update -y && \
#     apt-get install -y --no-install-recommends git && \
#     pip install poetry

# COPY ./pyproject.toml ./poetry.lock ./README.md /tmp/

# RUN sed -i -e 's/>=3.10,<=3.13/>=3.10,<3.12/g' pyproject.toml && poetry lock && \
#     poetry add git+${GAN_REPO}@${GAN_BRANCH} && \
#     git clone ${GAN_REPO} -b ${GAN_BRANCH} /tmp/code

ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim AS runner

# image build step variables
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USER_NAME=job
ARG WORK_HOME=/opt/cgan
ARG GAN_REPO=https://github.com/jaysnm/ensemble-cgan.git
ARG GAN_BRANCH=main

# install system libraries
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends git rsync ssh ca-certificates pkg-config \
    libgdal-dev libgeos-dev libproj-dev gdal-bin libcgal-dev libxml2-dev libsqlite3-dev  \
    gcc g++ dvipng libfontconfig-dev libjpeg-dev libspng-dev libx11-dev libgbm-dev git \
    libeccodes-dev libeccodes-tools && mkdir -p ${WORK_HOME}/.local/bin ${WORK_HOME}/.ssh


RUN groupadd --gid ${GROUP_ID} ${USER_NAME} && \
    useradd --home-dir ${WORK_HOME} --uid ${USER_ID} --gid ${GROUP_ID} ${USER_NAME} && \
    chown -Rf ${USER_NAME}:${USER_NAME} ${WORK_HOME}

USER ${USER_NAME}
WORKDIR ${WORK_HOME}
ENV PATH=${WORK_HOME}/.local/bin:$PATH

RUN git clone ${GAN_REPO} -b ${GAN_BRANCH} ${WORK_HOME}/ensemble-cgan && \
    cd ${WORK_HOME}/ensemble-cgan && pip install --no-cache-dir -e .

COPY --chown=${USER_NAME}:root ./pyproject.toml ./poetry.lock ./README.md ${WORK_HOME}/
COPY --chown=${USER_NAME}:root ./fastcgan ${WORK_HOME}/fastcgan
RUN pip install --no-cache-dir -e .

CMD ["python", "fastcgan/jobs/manager.py"]
