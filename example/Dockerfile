FROM python:3.11-slim

RUN apt update && apt install -y g++

COPY ./requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

COPY . /src

WORKDIR /src
EXPOSE 8000

CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" ]
