import http.server
import ssl
import sys

HOST = '0.0.0.0'
PORT = 8000
CERT_FILE = 'server.crt'
KEY_FILE = 'server.key'

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS Headers (Allow Cross-Origin Fetch Requests)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        # Add Content-Security-Policy (Allow HTTP and HTTPS Fetches)
        self.send_header('Content-Security-Policy', "connect-src *;")

        super().end_headers()

if __name__ == "__main__":
    handler = CustomHTTPRequestHandler
    httpd = http.server.HTTPServer((HOST, PORT), handler)

    try:
        httpd.socket = ssl.wrap_socket(httpd.socket,
                                        keyfile=KEY_FILE,
                                        certfile=CERT_FILE,
                                        server_side=True)
        print(f"Serving HTTPS on https://{HOST}:{PORT}")
        httpd.serve_forever()

    except FileNotFoundError:
        print(f"Error: Could not find {CERT_FILE} or {KEY_FILE}.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        httpd.server_close()
