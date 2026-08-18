FROM nginx:1.28-alpine

LABEL app="pg-sa-frontend"
LABEL version="1.0"

COPY . /usr/share/nginx/html

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx","-g","daemon off;"]
