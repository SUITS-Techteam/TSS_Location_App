from http.server import SimpleHTTPRequestHandler, HTTPServer
import ssl
import requests
import math
from urllib.parse import parse_qs
import os

# === Configuration ===
HOST = '0.0.0.0'
PORT = 8443  # Single port for everything
TARGET_HTTP_URL = "http://192.168.51.110:14141"

CERT_FILE = 'server.crt'
KEY_FILE = 'server.key'

ORIGIN_LAT = 29.56441
ORIGIN_LON = -95.08245
DUST_ORIGIN_X = -5762.13781
DUST_ORIGIN_Y = -10076.5894
MOON_RADIUS = 1737400  # meters

position_buffers = {'eva1': {}, 'eva2': {}}

def convert_lat_to_lunar_y(lat):
    lat_rad = math.radians(lat)
    origin_lat_rad = math.radians(ORIGIN_LAT)
    delta_y = MOON_RADIUS * (lat_rad - origin_lat_rad)
    return DUST_ORIGIN_Y + delta_y

def convert_lon_to_lunar_x(lon):
    lon_rad = math.radians(lon)
    origin_lon_rad = math.radians(ORIGIN_LON)
    avg_lat_rad = math.radians(ORIGIN_LAT)
    delta_x = MOON_RADIUS * (lon_rad - origin_lon_rad) * math.cos(avg_lat_rad)
    return DUST_ORIGIN_X + delta_x

class UnifiedHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # CORS and Security Policy
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Security-Policy', "connect-src *;")
        super().end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data_bytes = self.rfile.read(content_length)
        post_data = post_data_bytes.decode('utf-8')

        print("\n--- RAW POST DATA ---")
        print(f"Decoded: {post_data}")

        parsed_data = parse_qs(post_data)

        for eva in ['eva1', 'eva2']:
            posx_key = f"imu_{eva}_posx"
            posy_key = f"imu_{eva}_posy"

            if posx_key in parsed_data:
                position_buffers[eva]['posx'] = float(parsed_data[posx_key][0])

            if posy_key in parsed_data:
                position_buffers[eva]['posy'] = float(parsed_data[posy_key][0])

            if 'posx' in position_buffers[eva] and 'posy' in position_buffers[eva]:
                lon = position_buffers[eva]['posx']
                lat = position_buffers[eva]['posy']

                lunar_x = convert_lon_to_lunar_x(lon)
                lunar_y = convert_lat_to_lunar_y(lat)

                print(f"[{eva.upper()}] Converted Lunar Coords: X={lunar_x}, Y={lunar_y}")

                try:
                    requests.post(TARGET_HTTP_URL, data=f"imu_{eva}_posx={lunar_x}", timeout=5)
                    requests.post(TARGET_HTTP_URL, data=f"imu_{eva}_posy={lunar_y}", timeout=5)
                    print(f"Forwarded to backend successfully for {eva.upper()}")
                except Exception as e:
                    print(f"Error forwarding request: {e}")

                position_buffers[eva].clear()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

if __name__ == "__main__":
   
    httpd = HTTPServer((HOST, PORT), UnifiedHandler)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"HTTPS Server running on https://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        httpd.server_close()
