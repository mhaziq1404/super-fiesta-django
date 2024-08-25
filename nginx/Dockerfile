FROM nginx:latest

RUN apt-get update && apt-get install -y nginx openssl
RUN mkdir /etc/nginx/ssl
RUN openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/key.pem \
-out /etc/nginx/ssl/cert.pem -subj "/C=MY/ST=Kuala Lumpur/L=Sunway/O=42KL/OU=42KL/CN=nwai-kea"
RUN chmod 700 /etc/nginx/ssl

RUN rm -rf /etc/nginx/conf.d/default.conf
COPY ./conf/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 8081
EXPOSE 4430

CMD ["nginx", "-g", "daemon off;"]