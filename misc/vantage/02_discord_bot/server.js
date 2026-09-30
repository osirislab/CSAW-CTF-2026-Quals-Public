// Single entrypoint for both ways this runs.
//
//   - Locally: run directly, `node server.js`.
//   - Vercel: detected automatically as a `server` entrypoint because it calls
//     server.listen() at module load, then captured as a Vercel Function.
//
// Both receive plain Node IncomingMessage/ServerResponse objects, so the same
// raw-body signature verification in lib/interactions.js works identically on
// each. That handler is written in the Vercel res.status().json() style, which
// adaptResponse() below provides over a standard ServerResponse.

import http from 'node:http';
import handler from './lib/interactions.js';

const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || '0.0.0.0';

const REQUIRED_ENV = ['DISCORD_PUBLIC_KEY'];
const missing = REQUIRED_ENV.filter((name) => !process.env[name]);
if (missing.length) {
  console.error(`Missing required environment variables: ${missing.join(', ')}`);
  // Running locally, crashing is the right signal — the misconfiguration is
  // obvious immediately. On Vercel the module is also loaded while building,
  // where exiting would fail the deploy instead, so there we log and keep
  // serving; requests will 500 until the variable is set.
  if (!process.env.VERCEL) {
    process.exit(1);
  }
}

// Vercel's res helpers, reimplemented over a plain ServerResponse.
function adaptResponse(res) {
  return {
    status(code) {
      res.statusCode = code;
      return this;
    },
    send(body) {
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      res.end(body);
    },
    json(payload) {
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.end(JSON.stringify(payload));
    },
  };
}

const server = http.createServer(async (req, res) => {
  // Plain liveness probe — no signature, no Discord.
  if (req.method === 'GET' && (req.url === '/health' || req.url === '/healthz')) {
    res.statusCode = 200;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.end(JSON.stringify({ status: 'ok' }));
    return;
  }

  if (!req.url?.startsWith('/api/interactions')) {
    res.statusCode = 404;
    res.end('Not found');
    return;
  }

  try {
    await handler(req, adaptResponse(res));
  } catch (error) {
    console.error('Interaction handler failed:', error);
    if (!res.headersSent) {
      res.statusCode = 500;
      res.end('Internal server error');
    }
  }
});

// Drain on shutdown instead of dying mid-request.
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => {
    console.log(`${signal} received, shutting down`);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 10_000).unref();
  });
}

server.listen(PORT, HOST, () => {
  console.log(`fingerprint bot listening on http://${HOST}:${PORT}/api/interactions`);
});
