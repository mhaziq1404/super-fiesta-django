# FROM python:3.12-alpine as builder

# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# WORKDIR /app
# COPY ./requirements.txt .

# RUN pip install --upgrade pip && pip install flake8
# COPY . /app

# RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# FROM python:3.12-alpine 


# RUN mkdir /home/app
# ENV HOME=/home/app
# RUN mkdir /home/app/web
# ENV APP=/home/app/web
# WORKDIR $APP

# RUN pip install --upgrade pip && pip install netcat
# COPY --from=builder /app/wheels /wheels
# COPY --from=builder /app/requirements.txt .
# RUN pip install --upgrade pip
# RUN pip install --no-cache /wheels/*

# COPY ./entrypoint.sh .
# RUN sed -i 's/\r$//g' $APP/entrypoint.sh
# RUN chmod +x $APP/entrypoint.sh

# COPY . $APP

# RUN addgroup -S user && adduser -S user -G user

# RUN chown -R user:user $APP

# USER user

# EXPOSE 8000

# ENTRYPOINT [ "/home/app/web/entrypoint.sh" ]

# pull official base image
FROM python:3.12-alpine

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN apk update && apk upgrade
RUN apk add --no-cache bash pkgconfig gcc openldap libcurl libffi-dev musl-dev libc-dev zlib-dev jpeg-dev libjpeg-turbo-dev
RUN rm -rf /var/cache/apk/*
RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py
RUN pip install --upgrade pip
RUN pip install setuptools wheel
RUN pip config set --user global.trusted-host files.pythonhosted.org
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .

# RUN python manage.py migrate
# RUN python manage.py runserver