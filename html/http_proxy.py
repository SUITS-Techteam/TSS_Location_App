from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import requests

# Proxy Configuration
PROXY_HOST = '0.0.0.0'
PROXY_PORT = 8443  # HTTPS port
TARGET_HTTP_URL = "http://192.168.50.182:14141"  # Your real HTTP server

CERT_FILE = 'proxy.crt'
KEY_FILE = 'proxy.key'

class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data_bytes = self.rfile.read(content_length)

    # Raw logging
        print("\n--- RAW POST DATA ---")
        print(f"Raw Bytes: {post_data_bytes}")  # This will show raw byte content
        print(f"Raw Bytes Decoded as ISO-8859-1: {post_data_bytes.decode('ISO-8859-1')}")
        print(f"Raw Bytes Decoded as UTF-8: {post_data_bytes.decode('utf-8', errors='replace')}")
        print("----------------------\n")

        # Forward the exact raw data without modifying it
        try:
            response = requests.post(TARGET_HTTP_URL, data=post_data_bytes, timeout=5)
            self.send_response(response.status_code)
            self.end_headers()
            self.wfile.write(response.content)
        except Exception as e:
            print(f"Error forwarding request: {e}")
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b"Error forwarding request.")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"This is the HTTPS Proxy Server.")

if __name__ == "__main__":
    httpd = HTTPServer((PROXY_HOST, PROXY_PORT), ProxyHandler)
    httpd.socket = ssl.wrap_socket(httpd.socket,
                                    certfile=CERT_FILE,
                                    keyfile=KEY_FILE,
                                    server_side=True)
    print(f"Proxy HTTPS Server running on https://{PROXY_HOST}:{PROXY_PORT}")
    httpd.serve_forever()
