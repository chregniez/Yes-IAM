#!python3

import time
import mysql.connector
import socket
from getmac import get_mac_address
import subprocess
import os
import sys
import platform
import smtplib, ssl
import getpass

SLEEP = 900 # Each x seconds the script checks if something changed

# Connection to database
HOST = "localhost"
USER = "root"
PASSWORD = ""

# Database & table
DATABASE = "in-tech"
TABLE = "users"

# Columns to retrieve
C_HOSTNAME = "hostname"
C_MAC = "mac"
C_IP = "ip"
C_PLATFORM = "platform"
C_USERNAME = "username"

# SMTP informations
# /!\ WARNING : It can be necessary to activate unsecured application (like for Gmail)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "noreply.harmony5@gmail.com"
SMTP_PASS = "c$4Svrg!Q*ZUtKS05h4oP0^7VzpjCf^t"
SMTP_RCPT = "noreply.harmony5@gmail.com" #"adminit@et.intechinfo.fr"
SMTP_SUBJ = "Erreur d'un utilisateur"
# /!\ WARNING : The text must contain only ASCII characters
SMTP_TEXT = ("Subject : {}\r\n"
    "\r\n"
    "L'utilisateur {} a modifie certaines informations de la machine {}. Ses nouvelles informations sont :\r\n"
    "Nom d'hote : {}\r\n"
    "Adresse MAC : {}\r\n"
    "Adresse IP : {}\r\n"
    "Platforme : {}\r\n"
    "Nom d'utilisateur : {}\r\n"
    "\r\n"
    "Les informations originelles etaient :\r\n"
    "Nom d'hote : {}\r\n"
    "Adresse MAC : {}\r\n"
    "Adresse IP : {}\r\n"
    "Platforme : {}\r\n"
    "Nom d'utilisateur : {}\r\n"
    "\r\n"
)

def get_hostname() -> str:
    return socket.gethostname()

def get_mac() -> str:
    return get_mac_address(ip=get_ip())

def get_ip() -> str:
    ip = "0.0.0.0"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        print("Network unreachable")
    return ip

def get_platform() -> str:
    return platform.system() + platform.release()

def get_username() -> str: 
    return getpass.getuser()

origin = (get_hostname(), get_mac(), get_ip(), get_platform(), get_username())

# Manage all interfaces
# Warning : Root privilege required for Linux
def interfaces(enable=False):
    if not enable:
        if platform.system() == "Windows":
            with subprocess.Popen(["wmic", "nic", "get", "index"], stdout=subprocess.PIPE) as proc:
                for line in proc.stdout:
                    os.system("wmic path win32_networkadapter where index={} call disable".format(line.decode("utf-8").strip()))
        else:
            os.system("ip link set `ip link show | cut -d: -f2 | sed -n '3~3p'` down")
    else:
        if platform.system() == "Windows":
            with subprocess.Popen(["wmic", "nic", "get", "index"], stdout=subprocess.PIPE) as proc:
                for line in proc.stdout:
                    os.system("wmic path win32_networkadapter where index={} call enable".format(line.decode("utf-8").strip()))
        else:
            os.system("ip link set `ip link show | cut -d: -f2 | sed -n '3~3p'` up")

def alert(mycursor):
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.ehlo()
    server.starttls(context = ssl.create_default_context())
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, SMTP_RCPT, SMTP_TEXT.format(SMTP_SUBJ, 
        origin[0], platform.system(),
        get_hostname(), get_mac(), get_ip(), get_platform(), get_username(), 
        origin[0], origin[1], origin[2], origin[3], origin[4])
    )
    server.quit()

if len(sys.argv) == 2:
    if sys.argv[1] == "--enable":
        interfaces(True)
        os._exit(0)

while True:
    try:
        mydb = mysql.connector.connect(
            host = HOST,
            user = USER,
            password = PASSWORD,
            database = DATABASE
        )
    
        mycursor = mydb.cursor()
        
        while True:
            mycursor.execute("SELECT * FROM {} WHERE {} = '{}' AND {} = '{}' AND {} = '{}' AND {} = '{}' AND {} = '{}'".format(TABLE, 
                C_HOSTNAME, get_hostname(), 
                C_MAC, get_mac(),
                C_IP, get_ip(),
                C_PLATFORM, get_platform(),
                C_USERNAME, get_username()
            ))
            
            # If the user has not been found in database
            if len(mycursor.fetchall()) != 1:
                print("Something is wrong")
                alert(mycursor)
                while True:
                    interfaces()
                    time.sleep(1)
            time.sleep(SLEEP)
    except ConnectionRefusedError:
        print("Connection refused")
    except mysql.connector.errors.InterfaceError:
        print("Connection failed")
    time.sleep(5)