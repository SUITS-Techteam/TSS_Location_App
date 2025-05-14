from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import requests
import math
from urllib.parse import parse_qs

# Proxy Configuration
PROXY_HOST = '0.0.0.0'
PROXY_PORT = 8443
TARGET_HTTP_URL = "http://192.168.51.201:14141"

CERT_FILE = 'proxy.crt'
KEY_FILE = 'proxy.key'

ORIGIN_LAT = 29.56441
ORIGIN_LON = -95.08245
DUST_ORIGIN_X = -5762.13781
DUST_ORIGIN_Y = -10076.5894
MOON_RADIUS = 1737400  # meters

# Buffers for EVA1 and EVA2
position_buffers = {
    'eva1': {},
    'eva2': {}
}

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

class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data_bytes = self.rfile.read(content_length)
        post_data = post_data_bytes.decode('utf-8')

        # print("\n--- RAW POST DATA ---")
        # print(f"Decoded: {post_data}")

        parsed_data = parse_qs(post_data)

        for eva in ['eva1', 'eva2']:
            # Process posx
            posx_key = f"imu_{eva}_posx"
            if posx_key in parsed_data:
                posx_val = float(parsed_data[posx_key][0])
                position_buffers[eva]['posx'] = posx_val

            # Process posy
            posy_key = f"imu_{eva}_posy"
            if posy_key in parsed_data:
                posy_val = float(parsed_data[posy_key][0])
                position_buffers[eva]['posy'] = posy_val

            # Perform conversion if both posx and posy are available
            if 'posx' in position_buffers[eva] and 'posy' in position_buffers[eva]:
                lon = position_buffers[eva]['posx']
                lat = position_buffers[eva]['posy']

                lunar_x = convert_lon_to_lunar_x(lon)
                lunar_y = convert_lat_to_lunar_y(lat)

                print(f"[{eva.upper()}] Converted to Lunar Coords: X={lunar_x}, Y={lunar_y}")

                # Forward to backend
                requests.post(TARGET_HTTP_URL, data=f"imu_{eva}_posx={lunar_x}", timeout=5)
                requests.post(TARGET_HTTP_URL, data=f"imu_{eva}_posy={lunar_y}", timeout=5)

                # Clear buffer for this EVA
                position_buffers[eva].clear()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"This is the HTTPS Proxy Server with EVA support.")

if __name__ == "__main__":
    httpd = HTTPServer((PROXY_HOST, PROXY_PORT), ProxyHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    print(f"Proxy HTTPS Server running on https://{PROXY_HOST}:{PROXY_PORT}")
    httpd.serve_forever()
