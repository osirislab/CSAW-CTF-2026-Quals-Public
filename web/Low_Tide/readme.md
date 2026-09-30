
# Low Tide

## Running the challenge

1. Open a terminal in this folder.
2. Build all containers.

```
docker compose build
```

3. Start every container.

```
docker compose up
```

4. Check that seven containers are running.

```
docker compose ps
```

The entry page loads at port 8000. The load balancer answers at
port 8081.

5. Stop everything when finished.

```
docker compose down
```

## Troubleshooting

Port already in use. Another program on the machine is already using
port 8000 or 8081. Close that program, or open `docker-compose.yml`
and change the left side of the port mapping to a free port.

Containers exit right after starting. Run this command and read the
output for the failing service.

```
docker compose logs
```

Empty response or connection refused. Confirm the containers are
running with `docker compose ps`. If nothing appears, the build did
not finish. Run `docker compose build` again and watch for errors.

A request always gets rejected. The request must include the exact
required header value. It must also be sent to the load balancer
address, not directly to any individual station.

Changes to a file do not appear after editing. Docker keeps a cached
image from the last build. Rebuild with no cache.

```
docker compose build --no-cache
```

Then bring the containers up again.

A request works once and later requests fail. This platform limits
how many requests can be sent in a short span, and limits how many
wrong attempts a session gets before it moves elsewhere. This is
expected. Wait for the stated cooldown, then continue.

To reset everything to a clean state, remove all containers and
images, then rebuild.

```
docker compose down --rmi all -v
docker compose build --no-cache
docker compose up
```
