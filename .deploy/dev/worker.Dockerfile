FROM public.ecr.aws/n3f5h0h1/appello-baseimage:3.8-slim-buster

# RUN pip install celery[redis]

WORKDIR /src
COPY . .

RUN pip install -r requirements.txt \
    && apt-get -y purge gcc 

#CMD [ "celery", "-A", "zen worker", "-l", "info" ]
CMD [ "bash", "run-worker.sh" ]
