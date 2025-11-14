#!/usr/bin/env python3

from http.server import SimpleHTTPRequestHandler, HTTPServer
import ssl
import math
from urllib.parse import parse_qs
import os
import socket
import struct
import time

# === Configuration ===
HOST = '192.168.51.110'
PORT = 8000

TARGET_UDP_IP = "192.168.51.110"
TARGET_UDP_PORT = 14141

CERT_FILE = 'server.crt'
KEY_FILE = 'server.key'

UDP_COMMANDS = {
    'eva1_posx': 2017,
    'eva1_posy': 2018,
    'eva1_heading': 2019,
    'eva2_posx': 2020,
    'eva2_posy': 2021,
    'eva2_heading': 2022,
}

udp_socket = None

ORIGIN_LAT = 29.5643270
ORIGIN_LON = -95.0813360

#hotel coords
#ORIGIN_LAT = 29.5244187
#ORIGIN_LON = -95.122330161

DUST_ORIGIN_X = -5667.10
DUST_ORIGIN_Y = -10058.13
EARTH_RADIUS = 6371000  # meters

position_buffers = {'eva1': {}, 'eva2': {}}

def build_udp_packet(command_id, float_value):
    packet = struct.pack('>I', int(time.time()))
    packet += struct.pack('>I', command_id)
    packet += struct.pack('>f', float_value)
    return packet

def send_udp_packet(command_id, float_value):
    try:
        packet = build_udp_packet(command_id, float_value)
        udp_socket.sendto(packet, (TARGET_UDP_IP, TARGET_UDP_PORT))
    except Exception as e:
        print(f"Error sending UDP packet: {e}")

def convert_lat_to_lunar_y(lat):
    lat_rad = math.radians(lat)
    origin_lat_rad = math.radians(ORIGIN_LAT)
    delta_y = EARTH_RADIUS * (lat_rad - origin_lat_rad)
    return DUST_ORIGIN_Y + delta_y

def convert_lon_to_lunar_x(lon, lat):
    lon_rad = math.radians(lon)
    origin_lon_rad = math.radians(ORIGIN_LON)
    current_lat_rad = math.radians(lat)
    delta_x = EARTH_RADIUS * (lon_rad - origin_lon_rad) * math.cos(current_lat_rad)
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

        parsed_data = parse_qs(post_data)

        for eva in ['eva1', 'eva2']:
            posx_key = f"imu_{eva}_posx"
            posy_key = f"imu_{eva}_posy"
            head_key  = f"imu_{eva}_heading"

            if posx_key in parsed_data:
                position_buffers[eva]['posx'] = float(parsed_data[posx_key][0])

            if posy_key in parsed_data:
                position_buffers[eva]['posy'] = float(parsed_data[posy_key][0])

            if head_key in parsed_data and parsed_data[head_key][0] != 'null':
                position_buffers[eva]['heading'] = float(parsed_data[head_key][0])
                head = position_buffers[eva]['heading']
                heading_cmd = UDP_COMMANDS[f"{eva}_heading"]
                send_udp_packet(heading_cmd, head)

            if 'posx' in position_buffers[eva] and 'posy' in position_buffers[eva]:
                lon = position_buffers[eva]['posx']
                lat = position_buffers[eva]['posy']

                lunar_x = convert_lon_to_lunar_x(lon, lat)
                lunar_y = convert_lat_to_lunar_y(lat)

                posx_cmd = UDP_COMMANDS[f"{eva}_posx"]
                posy_cmd = UDP_COMMANDS[f"{eva}_posy"]
                send_udp_packet(posx_cmd, lunar_x)
                send_udp_packet(posy_cmd, lunar_y)

                position_buffers[eva].clear()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def translate_path(self, path):
        return os.path.join(os.getcwd(), path.lstrip("/"))

if __name__ == "__main__":
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except Exception as e:
        print(f"Failed to create UDP socket: {e}")
        exit(1)

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
        if udp_socket:
            udp_socket.close()
