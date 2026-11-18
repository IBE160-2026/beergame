FROM caddy:2.11.9

# Built from the repo root (`docker build -f proxy/Dockerfile .`), as compose and Railway do.
COPY proxy/Caddyfile /etc/caddy/Caddyfile

EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
