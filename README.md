# Running the position app: 
If you are using python3 you can run: 

`./https_server.py`

Otherwise run: 

`python server_http.py`

Then start your TSS server. 

# Generate Certificates
To generate the correct certificats for your machine do the following: 
1. Open the file "openssl_local.cnf"
2. update the CN and IP.1 ip addresses to match your host machine.
3.  Run:
   
    `openssl req -x509 -newkey rsa:4096 -nodes -keyout server.key -out server.crt -days 365 -config openssl_local.cnf -extensions req_ext`

This will generate the cert and overwrite the old one. 
