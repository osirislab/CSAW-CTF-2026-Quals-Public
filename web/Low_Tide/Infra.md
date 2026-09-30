# CSAW Quals 2026 Submission Info

## Challenge Name
Low Tide

## Final Flag
csaw{time_sensitive_scada_proxy_chain}

## Challenge Description (player facing)
A water treatment utility's remote monitoring system has been left
online with an old technician login page still reachable. The login
does not work anymore, but the page was never actually taken down.

## Files Included

```
deployment/
├── docker-compose.yml
├── phase0-static/
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── robots.txt
│   └── assets/
│       ├── app.js
│       └── style.css
├── loadbalancer/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── lb_app.py
├── station/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── station_app.py
└── admin-relay/
    ├── Dockerfile
    ├── requirements.txt
    └── admin_app.py

player/
└── (nothing, this is a remote web challenge, players only receive
     a connection URL, no downloadable files)
```

Excluded entirely, kept with the organizers only, not sent anywhere:

```
solve.py       - reference solver, phase one only
full_solve.py  - full reference solver, every stage
test_all.py    - automated test suite covering every stage- only in production
README.md      - internal build notes, not meant for players
```
