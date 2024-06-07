FROM python:3.11-slim-bookworm
RUN apt-get update
RUN apt-get install -y curl

RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get remove nodejs && \
    rm -rf /usr/local/bin/node* && \
    rm -rf /usr/local/bin/npm* && \
    rm -rf /etc/apt/sources.list.d/nodesource.list && \
    apt install -y nodejs && \
    apt install -y npm && \
    npm install -g bower

RUN set -ex \
    # install system build deps
&&  apt install -y gcc \
    # install system runtime deps
&&  apt install -y libpq-dev \
&&  apt install -y libpango-1.0-0 libpangoft2-1.0-0 \
    # install python app requirements
&&  pip install poetry

RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PYTHONUNBUFFERED 1
WORKDIR /srv/app

RUN npm install jsplumb@1.7.9
COPY bower.json .bowerrc /srv/app/
RUN bower --allow-root install
RUN sed -i 's/\/assets\/images\/ng-emoji-picker/\/static\/\/static\/lib\/ng-emoji-picker\/img/g' /srv/app/staticfiles/lib/ng-emoji-picker/js/jquery.emojiarea.js
RUN sed -i 's/\/assets\/images\/ng-emoji-picker/\/static\/\/static\/lib\/ng-emoji-picker\/img/g' /srv/app/staticfiles/lib/ng-emoji-picker/css/emoji.css

COPY django-multisite.tar.gz /srv/app/
RUN tar xvzf django-multisite.tar.gz
RUN python django-multisite/setup.py install
RUN rm -fr django-multisite django-multisite.tar.gz django_multisite.egg-info

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
  && poetry lock --no-update && poetry install --no-interaction --no-ansi  \
  &&  rm -rf ~/.cache poetry.lock pyproject.toml \
    # remove system build deps
  &&  apt purge -y --autoremove gcc

COPY . .
RUN set -ex \
    # collect app static
&&  python manage.py collectstatic --noinput
