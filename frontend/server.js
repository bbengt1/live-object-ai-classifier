/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Custom HTTPS server for Next.js production
 *
 * This server enables HTTPS for the Next.js frontend using the same
 * SSL certificates configured for the backend. It also handles WebSocket
 * proxying for live camera streams (Story P16-2).
 *
 * Usage:
 *   SSL_CERT_FILE=/path/to/cert.pem SSL_KEY_FILE=/path/to/key.pem node server.js
 *
 * Environment variables:
 *   SSL_CERT_FILE - Path to SSL certificate file (required)
 *   SSL_KEY_FILE  - Path to SSL private key file (required)
 *   PORT          - Port to listen on (default: 3000)
 *   HOSTNAME      - Hostname to bind to (default: 0.0.0.0)
 *   BACKEND_URL   - Backend URL for API/WebSocket proxying (default: http://localhost:8000)
 */

const { createServer } = require('https');
const { parse } = require('url');
const next = require('next');
const fs = require('fs');
const net = require('net');

const dev = process.env.NODE_ENV !== 'production';
const hostname = process.env.HOSTNAME || '0.0.0.0';
const port = parseInt(process.env.PORT || '3000', 10);

// Backend URL for WebSocket proxying
const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// SSL certificate paths from environment variables
const certFile = process.env.SSL_CERT_FILE;
const keyFile = process.env.SSL_KEY_FILE;

// Validate SSL configuration
if (!certFile || !keyFile) {
  console.error('Error: SSL_CERT_FILE and SSL_KEY_FILE environment variables are required');
  console.error('Usage: SSL_CERT_FILE=/path/to/cert.pem SSL_KEY_FILE=/path/to/key.pem node server.js');
  process.exit(1);
}

// Check if certificate files exist
if (!fs.existsSync(certFile)) {
  console.error(`Error: Certificate file not found: ${certFile}`);
  process.exit(1);
}

if (!fs.existsSync(keyFile)) {
  console.error(`Error: Key file not found: ${keyFile}`);
  process.exit(1);
}

// Read SSL certificates
const httpsOptions = {
  cert: fs.readFileSync(certFile),
  key: fs.readFileSync(keyFile),
};

// Parse backend URL for WebSocket proxying
const backendUrlParsed = new URL(backendUrl);
const backendHost = backendUrlParsed.hostname;
const backendPort = backendUrlParsed.port || (backendUrlParsed.protocol === 'https:' ? 443 : 80);

// Initialize Next.js app
const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = createServer(httpsOptions, async (req, res) => {
    // Debug: check if WebSocket requests come through the normal handler
    if (req.headers.upgrade === 'websocket') {
      console.log(`DEBUG: WebSocket request in normal handler! ${req.url}`);
    }
    try {
      const parsedUrl = parse(req.url, true);
      await handle(req, res, parsedUrl);
    } catch (err) {
      console.error('Error occurred handling', req.url, err);
      res.statusCode = 500;
      res.end('Internal Server Error');
    }
  });

  // Handle WebSocket upgrade requests for streaming endpoints (Story P16-2)
  // Uses raw socket connection to backend for proper byte-level proxying
  server.on('upgrade', (req, socket, head) => {
    const { pathname } = parse(req.url, true);

    // Proxy WebSocket connections for camera streams and other WS endpoints
    if ((pathname.startsWith('/api/v1/cameras/') && pathname.endsWith('/stream')) ||
        pathname === '/ws' || pathname.startsWith('/ws/')) {
      console.log(`WebSocket upgrade: ${pathname} -> ${backendHost}:${backendPort}${pathname}`);
      console.log(`  Head buffer length: ${head.length}`);

      // TEST: Just send a fake 101 response, don't connect to backend
      // This is to see if Next.js is also sending a 101
      console.log(`  TEST: Sending fake 101 to client`);
      socket.write('HTTP/1.1 101 Switching Protocols\r\n');
      socket.write('X-Test: from-our-handler\r\n');
      socket.write('\r\n');

      // Keep socket open for a moment
      setTimeout(() => {
        console.log(`  TEST: Closing socket`);
        socket.destroy();
      }, 2000);
    } else {
      // Let Next.js handle other WebSocket connections (e.g., HMR in dev mode)
      socket.destroy();
    }
  });

  server
    .once('error', (err) => {
      console.error('Server error:', err);
      process.exit(1);
    })
    .listen(port, hostname, () => {
      console.log(`> Ready on https://${hostname}:${port}`);
      console.log(`> SSL Certificate: ${certFile}`);
      console.log(`> Backend WebSocket proxy: ${backendUrl}`);
    });
});
