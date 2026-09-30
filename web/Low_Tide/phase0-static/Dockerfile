FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY .htaccess /usr/share/nginx/html/.htaccess
COPY robots.txt /usr/share/nginx/html/robots.txt
COPY assets/ /usr/share/nginx/html/assets/

EXPOSE 80
