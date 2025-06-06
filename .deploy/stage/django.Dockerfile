FROM public.ecr.aws/n3f5h0h1/appello-baseimage:3.8-slim-buster

RUN pip install gunicorn

WORKDIR /src
COPY . .

RUN pip install -r requirements.txt \
    && apt-get -y purge gcc 

CMD [ "bash", "run.sh" ]
