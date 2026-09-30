FROM php:8.2-apache

RUN apt-get update && apt-get install -y libsqlite3-dev \
    && docker-php-ext-install pdo_sqlite \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV APACHE_DOCUMENT_ROOT=/var/www/html/public
RUN sed -rie "s!/var/www/html!${APACHE_DOCUMENT_ROOT}!g" /etc/apache2/sites-available/*.conf
RUN sed -rie "s!/var/www!${APACHE_DOCUMENT_ROOT}!g" /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

WORKDIR /var/www/html

COPY . /var/www/html
RUN php src/init.php
RUN admin_role1=$(cat /dev/urandom | tr -dc "a-z0-9" | head -c 32) \
    && admin_role2=$(cat /dev/urandom | tr -dc "a-z0-9" | head -c 32) \
    && sed -i "s/placeholder_admin_role1/$admin_role1/g" config/config.ini \
    && sed -i "s/placeholder_admin_role2/$admin_role2/g" config/config.ini
RUN chown -R www-data:www-data /var/www/html
EXPOSE 80