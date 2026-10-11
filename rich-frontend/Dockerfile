FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html app.js style.css sw.js manifest.json config.js favicon.png Rapidbay.apk /usr/share/nginx/html/
COPY img /usr/share/nginx/html/img
COPY lib /usr/share/nginx/html/lib
COPY docker-entrypoint.sh /docker-entrypoint.d/40-rapidbay-config.sh
COPY .env* /tmp/rapidbay-env/
RUN chmod +x /docker-entrypoint.d/40-rapidbay-config.sh \
    && mkdir -p /etc/rapidbay \
    && if [ -f /tmp/rapidbay-env/.env ]; then cp /tmp/rapidbay-env/.env /etc/rapidbay/.env; fi \
    && rm -rf /tmp/rapidbay-env
