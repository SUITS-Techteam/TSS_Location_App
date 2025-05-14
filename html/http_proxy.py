from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import requests
import math
from urllib.parse import parse_qs

# Proxy Configuration
PROXY_HOST = '0.0.0.0'
PROXY_PORT = 8443  # HTTPS port
TARGET_HTTP_URL = "http://192.168.50.182:14141"  # Update with your backend server's IP

CERT_FILE = 'proxy.crt'
KEY_FILE = 'proxy.key'

ORIGIN_LAT = 29.56441
ORIGIN_LON = -95.08245
DUST_ORIGIN_X = -5762.13781
DUST_ORIGIN_Y = -10076.5894
MOON_RADIUS = 1737400  # meters

# Buffer to store the latest posx and posy values
position_buffer = {}

def convert_lat_to_lunar_y(lat):
    lat_rad = math.radians(lat)
    origin_lat_rad = math.radians(ORIGIN_LAT)
    delta_y = MOON_RADIUS * (lat_rad - origin_lat_rad)
    return DUST_ORIGIN_Y + delta_y

def convert_lon_to_lunar_x(lon):
    lon_rad = math.radians(lon)
    origin_lon_rad = math.radians(ORIGIN_LON)
    avg_lat_rad = math.radians(ORIGIN_LAT)  # Only ORIGIN_LAT used here
    delta_x = MOON_RADIUS * (lon_rad - origin_lon_rad) * math.cos(avg_lat_rad)
    return DUST_ORIGIN_X + delta_x

class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data_bytes = self.rfile.read(content_length)
        post_data = post_data_bytes.decode('utf-8')

        print("\n--- RAW POST DATA ---")
        print(f"Decoded: {post_data}")

        parsed_data = parse_qs(post_data)

        # Process posx
        if 'imu_eva1_posx' in parsed_data:
            posx_val = float(parsed_data['imu_eva1_posx'][0])
            position_buffer['posx'] = posx_val

        # Process posy
        if 'imu_eva1_posy' in parsed_data:
            posy_val = float(parsed_data['imu_eva1_posy'][0])
            position_buffer['posy'] = posy_val

        try:
            # If both posx and posy are available, perform the conversion and send
            if 'posx' in position_buffer and 'posy' in position_buffer:
                lon = position_buffer['posx']
                lat = position_buffer['posy']

                lunar_x = convert_lon_to_lunar_x(lon)
                lunar_y = convert_lat_to_lunar_y(lat)

                print(f"Converted to Lunar Coords: X={lunar_x}, Y={lunar_y}")

                # Forward converted values to HTTP server
                requests.post(TARGET_HTTP_URL, data=f"imu_eva1_posx={lunar_x}", timeout=5)
                requests.post(TARGET_HTTP_URL, data=f"imu_eva1_posy={lunar_y}", timeout=5)

                # Optionally, clear the buffer after processing
                position_buffer.clear()

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

        except Exception as e:
            print(f"Conversion or forwarding error: {e}")
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b"Error processing request.")

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
