FROM python

MAINTAINER Kseniya Epanchina 'rzksenia@yandex.ru'

WORKDIR /

COPY . /

RUN pip install cryptography
RUN pip install -r requirements.txt
RUN apt-get update && \
    apt-get install -y xclip
RUN pip install waitress

EXPOSE 3002

ENV PYTHONPATH "${PYTHONPATH}:/"

CMD ["python", "app/client.py"]

