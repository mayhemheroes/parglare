# Build Stage
FROM python:3.11-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=NONINTERACTIVE apt-get install -y build-essential git && \
    pip install --upgrade pip && \
    pip install atheris

ADD . /src
WORKDIR /src
RUN pip install .

CMD ["/src/mayhem/fuzz_grammar_parse.py"]
