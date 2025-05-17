# Running the position app: 
Run python server_http.py alongside the main TSS server
# Generate Certificates
The certificates are set for ip 192.168.51.110. If we need to run this on a differnt machine do the following: 
Open the file "openssl_local.cnf" update the CN and IP.1 ip addresses to match the new host machine. 
Next run: 

`openssl req -x509 -newkey rsa:4096 -nodes -keyout server.key -out server.crt -days 365 -config openssl_local.cnf -extensions req_ext`

This will generate the cert and overwrite the old one. 
