#!/usr/bin/env python3

# 20201020 - Add a function to add a single prefix to a local prefixlist - Dan
import cloudgenix
import argparse
from cloudgenix import jd, jd_detailed
import cloudgenix_settings
import sys
import logging
import os
import datetime
import collections
import csv
import ipaddress
from csv import DictReader
import time
from datetime import datetime, timedelta
import math
jdout = cloudgenix.jdout

# Global Vars
TIME_BETWEEN_API_UPDATES = 60       # seconds
REFRESH_LOGIN_TOKEN_INTERVAL = 7    # hours
SDK_VERSION = cloudgenix.version
SCRIPT_NAME = 'CloudGenix: Example script: Global Prefix'
SCRIPT_VERSION = "v1"

# Set NON-SYSLOG logging to use function name
logger = logging.getLogger(__name__)

####################################################################
# Read cloudgenix_settings file for auth token or username/password
####################################################################

sys.path.append(os.getcwd())
try:
    from cloudgenix_settings import CLOUDGENIX_AUTH_TOKEN

except ImportError:
    # Get AUTH_TOKEN/X_AUTH_TOKEN from env variable, if it exists. X_AUTH_TOKEN takes priority.
    if "X_AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
    elif "AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
    else:
        # not set
        CLOUDGENIX_AUTH_TOKEN = None

def get_all_routes(cgx):    
    
    global_subnet_list = []
    site_id2n = {}
    element_id2n = {}
    for site in cgx.get.sites().cgx_content['items']:
        if site["element_cluster_role"] == "SPOKE":
            print("Checking site " + site["name"])           
            ############################## Gather Elements ######################################
            element_list = []
            for elements in cgx.get.elements().cgx_content["items"]:
                element_id2n[elements["id"]] = elements["name"]
                if elements["site_id"] == site["id"]:
                    element_list.append(elements["id"])
                        
            ############################## Interface Routes ######################################
            try:
                for element in element_list:
                    for interface in cgx.get.interfaces(site_id=site['id'], element_id=element).cgx_content["items"]:
                        if interface["scope"] == "global":
                            try:
                                if interface['ipv4_config']:
                                    prefix = ipaddress.ip_network(interface['ipv4_config']['static_config']['address'], strict=False)
                                    if str(prefix) not in global_subnet_list:
                                        prefix_data = {}
                                        prefix_data["Site_Name"] = site["name"]
                                        prefix_data["Type"] = "Local Interface"
                                        prefix_data["Route"] = prefix
                                        global_subnet_list.append(prefix_data)
                            except:
                                print("Unabled to get IPv4 config from interface " + interface["name"])
            except:
                print("Unabled to get interfaces " + element_id2n[element])
            ############################## Static Routes ######################################
            try:
                for element in element_list:
                    for static in cgx.get.staticroutes(site_id=site['id'], element_id=element).cgx_content["items"]:
                        if static["scope"] == "global":
                            prefix = ipaddress.ip_network(static['destination_prefix'], strict=False)
                            if str(prefix) not in global_subnet_list:
                                prefix_data = {}
                                prefix_data["Site_Name"] = site["name"]
                                prefix_data["Type"] = "Static"
                                prefix_data["Route"] = prefix
                                global_subnet_list.append(prefix_data)
            except:
                print("Unabled to get static routes " + element_id2n[element])
                       
            ############################## BGP Routes ######################################
            try:
                bgp_id2n = {}
                for element in element_list:
                    bgp_list = []
                    for bgppeers in cgx.get.bgppeers(site_id=site["id"], element_id=element).cgx_content["items"]:
                        bgp_id2n[bgppeers["id"]] = bgppeers["name"]
                        if bgppeers["scope"] == "global":
                            bgp_list.append(bgppeers["id"])
                    for bgpstatus in cgx.get.bgppeers_status(site_id=site["id"], element_id=element).cgx_content["items"]:
                        if bgpstatus["id"] in bgp_list:
                            if bgpstatus["state"] == "Established" and bgpstatus["direction"] == "lan":
                                try:
                                    prefixes = cgx.get.bgppeers_reachableprefixes(site_id=site["id"], element_id=element, bgppeer_id=bgpstatus['id']).cgx_content['reachable_ipv4_prefixes']
                                    for prefix in prefixes:
                                        if prefix["network"] not in global_subnet_list:
                                            prefix_data = {}
                                            prefix_data["Site_Name"] = site["name"]
                                            prefix_data["Type"] = "BGP"
                                            prefix_data["Route"] = prefix["network"]
                                            global_subnet_list.append(prefix_data)
                                except:
                                    print("Unabled to get IPv4 prefixes from BGP peer " + bgp_id2n[bgpstatus['id']])
            except:
                print("Unabled to get BGP routes " + element_id2n[element])
    
    if global_subnet_list:
        csv_columns = []
        for key in global_subnet_list[0]:
            csv_columns.append(key)
    
        csv_file = "route_list.csv"
        try:
            with open(csv_file, 'w', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                for data in global_subnet_list:
                    try:
                        writer.writerow(data)
                    except:
                        print("Failed to write data for row")
                print("\nSaved route_list.csv file")
        except IOError:
            print("CSV Write Failed")
    else:
        print("No global interface, static or BGP routes found")
        
    return
                                          
def go():
    ############################################################################
    # Begin Script, parse arguments.
    ############################################################################

    # Parse arguments
    parser = argparse.ArgumentParser(description="{0}.".format(SCRIPT_NAME))

    # Allow Controller modification and debug level sets.
    controller_group = parser.add_argument_group('API', 'These options change how this program connects to the API.')
    controller_group.add_argument("--controller", "-C",
                                  help="Controller URI, ex. "
                                       "Alpha: https://api-alpha.elcapitan.cloudgenix.com"
                                       "C-Prod: https://api.elcapitan.cloudgenix.com",
                                  default=None)
    controller_group.add_argument("--insecure", "-I", help="Disable SSL certificate and hostname verification",
                                  dest='verify', action='store_false', default=True)
    login_group = parser.add_argument_group('Login', 'These options allow skipping of interactive login')
    login_group.add_argument("--email", "-E", help="Use this email as User Name instead of prompting",
                             default=None)
    login_group.add_argument("--pass", "-PW", help="Use this Password instead of prompting",
                             default=None)
    debug_group = parser.add_argument_group('Debug', 'These options enable debugging output')
    debug_group.add_argument("--debug", "-D", help="Verbose Debug info, levels 0-2", type=int,
                             default=0)
    config_group = parser.add_argument_group('Config', 'These options change how the configuration is generated.')
    
    args = vars(parser.parse_args())
                             
    ############################################################################
    # Instantiate API
    ############################################################################
    cgx_session = cloudgenix.API(controller=args["controller"], ssl_verify=args["verify"])

    # set debug
    cgx_session.set_debug(args["debug"])

    # ##########################################################################
    # Draw Interactive login banner, run interactive login including args above.
    ############################################################################
    print("{0} {1} ({2})\n".format(SCRIPT_NAME, SCRIPT_VERSION, cgx_session.controller))

    # check for token
    if CLOUDGENIX_AUTH_TOKEN and not args["email"] and not args["pass"]:
        cgx_session.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if cgx_session.tenant_id is None:
            print("AUTH_TOKEN login failure, please check token.")
            sys.exit()

    else:
        while cgx_session.tenant_id is None:
            cgx_session.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not cgx_session.tenant_id:
                user_email = None
                user_password = None

    ############################################################################
    # End Login handling, begin script..
    ############################################################################

    # get time now.
    curtime_str = datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S')

    # create file-system friendly tenant str.
    tenant_str = "".join(x for x in cgx_session.tenant_name if x.isalnum()).lower()
    cgx = cgx_session
    get_all_routes(cgx) 
    # end of script, run logout to clear session.

if __name__ == "__main__":
    go()