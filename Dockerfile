FROM python:3.11-slim-bullseye

RUN apt-get update
RUN apt-get install -y curl

RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get remove nodejs && \
    rm -rf /usr/local/bin/node* && \
    rm -rf /usr/local/bin/npm* && \
    rm -rf /etc/apt/sources.list.d/nodesource.list && \
    apt-get install -y nodejs && \
    apt-get install -y npm && \
    npm install -g bower

RUN apt-get update && apt-get install -y supervisor

RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PYTHONUNBUFFERED 1
WORKDIR /code
RUN npm install jsplumb@1.7.9
COPY bower.json .bowerrc /code/
RUN bower --allow-root install
RUN sed -i 's/\/assets\/images\/ng-emoji-picker/\/static\/\/static\/lib\/ng-emoji-picker\/img/g' /code/staticfiles/lib/ng-emoji-picker/js/jquery.emojiarea.js
RUN sed -i 's/\/assets\/images\/ng-emoji-picker/\/static\/\/static\/lib\/ng-emoji-picker\/img/g' /code/staticfiles/lib/ng-emoji-picker/css/emoji.css
COPY django-multisite.tar.gz /code/
RUN tar xvzf django-multisite.tar.gz
RUN python django-multisite/setup.py install
RUN rm -fr django-multisite django-multisite.tar.gz django_multisite.egg-info
COPY requirements.txt /code/
RUN pip install -r requirements.txt
RUN pip install ptvsd
RUN pip install https://github.com/darklow/django-suit/tarball/v2
COPY supervisor.conf /etc/supervisor/supervisor.conf
COPY supervisor.deploy.conf /etc/supervisor/supervisor.deploy.conf
COPY . /code/
RUN mkdir -p /vol/web/media
RUN mkdir -p /vol/web/static
RUN python manage.py collectstatic --noinput
CMD ["supervisord", "-c", "/etc/supervisor/supervisor.deploy.conf"]
