#! /usr/bin/python3
"""
This script provides handy tools for Apstra. Like changing the SZ name, updating device password etc.
Tested on Apstra:
4.2
4.1
4.0
"""

import os
import datetime
from apstra_function import *

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'


__author__ = "B.P.A. van Kampen"
__copyright__ = "Copyright 2024"
__license__ = "GPL"
__version__ = "0.1"
__maintainer__ = "B.P.A. van Kampen"
__email__ = "bartvankampen "
__status__ = "Beta"

# VARIABLE
aos_server = input('Apstra IP: ')
username = input('Enter your username: ')
password = getpass.getpass('Enter your password: ')

if os.name == 'nt':
    clear = "cls"
else:
    clear = 'clear' # CLEAR SCREEN STAMENT (CLS IF RUNNING ON WINDOWS, CLEAR FOR LINUX)

# AUTHENTICATE
aos_auth = apstra_authenticate(aos_server, username, password)

# SELECT BLUEPRINT
aos_blueprint = apstra_getblueprints(aos_server, aos_auth)

os.system(clear)
print("\nChoose service you want to use : ")
print("""
1 : Change SZ name 
2 : Change Node Password
3 : Change Password of All Nodes in DC
4 : Search in Global Configlets
5 : Multi-SSH
6 : 
7 : 
8 : Restore All nodes password to lab123 (for testing)
9 : Restore node password to lab123 (for testing)
0 : Exit
""")

choice = input("\nEnter your choice : ")

if choice == '1': # Change SZ Name
    os.system(clear)
    # SELECT SZ
    aos_sz = apstra_getsecurityzone(aos_server, aos_auth, aos_blueprint)
    # CHANGE SZ
    new_sz_name = input("Wat moet de nieuwe SZ naam zijn? ")
    if len(new_sz_name) > 15:
        print ("Error! Only 15 characters allowed!")
        sys.exit()
    apstra_updatesecurityzone(aos_server, aos_auth, aos_blueprint, aos_sz[0], new_sz_name, aos_sz[2])
    # Print Statement
    os.system(clear)
    print("Change has been applied (Not yet commited).")
    print("Before commiting, please change your configlets (if there are any) that contain the old SZ name!")
    print(f"!! CHANGE {aos_sz[1]} to {new_sz_name} !!")

    aos_configlet = apstra_seachconfiglet(aos_server, aos_auth, aos_sz[1])
    for i in aos_configlet[1]:
        print(f'Found {aos_sz[1]} in {aos_configlet[0][i]["display_name"]}:')
        print(aos_configlet[0][i]["generators"][0]["template_text"])
    q_changeitem = input(f"Term: {color.YELLOW}'{aos_sz[1]}'{color.END} vervangen voor {color.YELLOW}'{new_sz_name}'{color.END} (y/n): ")
    if q_changeitem != 'y':
        sys.exit()
    apstra_changeconfiglet(aos_server, aos_auth, aos_configlet[0], aos_configlet[1], aos_sz[1], new_sz_name)
    print("--------------------------------------\nResult:")
    configlet_result = apstra_seachconfiglet(aos_server, aos_auth, new_sz_name)
    configlet_result_names = []
    for i in configlet_result[1]:
        print(f'{configlet_result[0][i]["display_name"]}:')
        configlet_result_names.append(configlet_result[0][i]["display_name"])
        print(configlet_result[0][i]["generators"][0]["template_text"])
    print(f"--------------------------------------\nPlease reimport the following configlets:\n{color.YELLOW}{configlet_result_names}{color.END}")
elif (choice == '2' or choice == '9'): # Change Node Password
    os.system(clear)
    aos_node = apstra_getnode(aos_server, aos_auth, aos_blueprint) 

    #aos_node[1]=Hostname [1]=NodeID [2]=NodeSN [3]=Node MGT IP [4]=AgentID

    print(f"\nGathering Facts: \nNode Hostname: {aos_node[1]}. \nNode mgt IP: {aos_node[3]}. \nNode ID: {aos_node[0]}. \nNode SN: {aos_node[2]}. \n")
    use_radius = input('Account ' + username + ' gebruiken om in te loggen op de node (y/n)? ')
    if use_radius == 'n':
        node_username = input('Node username: ')
        node_password = getpass.getpass('Node password: ')
    else:
        node_username = username
        node_password = password
    node_ssh = ssh_login(node_username, node_password, aos_node[3])
    pw_apstra_mgr = generate_pw()
    pw_root = generate_pw()

    # Remove in production
    if choice == '9':
        pw_apstra_mgr = 'lab123'
        pw_root = 'lab123'

    print(f"\nDit worden de nieuwe wachtwoorden voor {aos_node[1]}. Sla deze nu op in de KeePass!")
    print(f"apstra_mgr: {pw_apstra_mgr}")
    print(f"root: {pw_root}")
    doorgaan = input('\nWachtwoord opgeslagen (y/n)? ')
    if doorgaan != 'y':
        sys.exit(1)
    apstra_changepassword(aos_server, aos_auth, aos_blueprint, aos_node, node_ssh, pw_apstra_mgr, pw_root)
    
elif (choice == '3' or choice == '8'):
    os.system(clear)
    aos_allnodes = apstra_getallnodes(aos_server, aos_auth, aos_blueprint)

    #Order nodes from A-Z
    order_nodes = sorted(aos_allnodes, key=lambda x: (aos_allnodes[x]['hostname']))
    aos_allnodes = {k: aos_allnodes[k] for k in order_nodes}
    
    print(f"Dit veranderd het wachtwoord van alle nodes in {aos_blueprint['label']}!")
    print(f"De volgende nodes zitten in deze blueprint:")
    for node in aos_allnodes:
        print(aos_allnodes[node]["hostname"])
    doorgaan = input('\nDoorgaan met deze actie (y/n)? ')
    if doorgaan != 'y':
        sys.exit(1)

    use_radius = input('Account ' + username + ' gebruiken om in te loggen op de node (y/n)? ')
    if use_radius == 'n':
        node_username = input('Node username: ')
        node_password = getpass.getpass('Node password: ')
    else:
        node_username = username
        node_password = password

    #Get directory where the script is running
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)

    #Order nodes on last number. (So the order is not LFS21, LFs22, what could harm the avaiability, but rather LFS21, LFS31, LFS41, LFS22 etc.)
    order_nodes = sorted(aos_allnodes, key=lambda x: (aos_allnodes[x]['hostname'][-1]))
    aos_allnodes = {k: aos_allnodes[k] for k in order_nodes}
    for node in aos_allnodes:
        aos_allnodes[node]["pw_apstra_mgr"] = generate_pw()
        aos_allnodes[node]["pw_root"] = generate_pw()
        # Remove in production
        if choice == '8':
            aos_allnodes[node]["pw_apstra_mgr"] = 'lab123'
            aos_allnodes[node]["pw_root"] = 'lab123'
        node_ssh = ssh_login(node_username, node_password, aos_allnodes[node]["mgmt_ip"])
        apstra_changeallpassword(aos_server, aos_auth, aos_blueprint, aos_allnodes[node], node_ssh)

    #Order nodes from A-Z
    order_nodes = sorted(aos_allnodes, key=lambda x: (aos_allnodes[x]['hostname']))
    aos_allnodes = {k: aos_allnodes[k] for k in order_nodes}

    filename=f'AOS_Password_Reset_{datetime.datetime.now().strftime("%m_%d_%Y-%H_%M")}.txt'
    file = open(filename, "w")

    for node in aos_allnodes:
        file.write("------------------------------------------------------\n")
        file.write(f'Device: {aos_allnodes[node]["hostname"]}\n')
        file.write(f'Password apstra_mgr: {aos_allnodes[node]["pw_apstra_mgr"]}\n')
        file.write(f'Password root: {aos_allnodes[node]["pw_root"]}\n')
        print("------------------------------------------------------")
        print(f'Device: {aos_allnodes[node]["hostname"]}')
        print(f'Password apstra_mgr: {aos_allnodes[node]["pw_apstra_mgr"]}')
        print(f'Password root: {aos_allnodes[node]["pw_root"]}')
    print("\nAll password changed, please save them!!!")
    print(f"Password are also stored in file {dname}\{filename} please delete after!")
    file.close()
    doorgaan = ''
    while doorgaan != 'y':
        doorgaan = input('\nWachtwoord opgeslagen (y/n)? ') 

elif choice == '4':
    search_item = input("Zoek in alle configlets naar: ")
    aos_configlet = apstra_seachconfiglet(aos_server, aos_auth, search_item)
    for i in aos_configlet[1]:
        print(f'Found {search_item} in {aos_configlet[0][i]["display_name"]}:')
        print(aos_configlet[0][i]["generators"][0]["template_text"])
    q_changeitem = input(f"Term: {color.YELLOW}'{search_item}'{color.END} vervangen (y/n): ")
    if q_changeitem != 'y':
        sys.exit()
    replace_item_with = input(f"Pas '{color.YELLOW}{search_item}{color.END}' aan naar: ")
    apstra_changeconfiglet(aos_server, aos_auth, aos_configlet[0], aos_configlet[1], search_item, replace_item_with)
    print("--------------------------------------\nResult:")
    configlet_result = apstra_seachconfiglet(aos_server, aos_auth, replace_item_with)
    configlet_result_names = []
    for i in configlet_result[1]:
        print(f'{configlet_result[0][i]["display_name"]}:')
        configlet_result_names.append(configlet_result[0][i]["display_name"])
        print(configlet_result[0][i]["generators"][0]["template_text"])
    print(f"--------------------------------------\nPlease reimport the following configlets:\n{color.YELLOW}{configlet_result_names}{color.END}")
elif choice == '5':
    os.system(clear)
    aos_allnodes = apstra_getallnodes(aos_server, aos_auth, aos_blueprint)

    #Order nodes from A-Z
    order_nodes = sorted(aos_allnodes, key=lambda x: (aos_allnodes[x]['hostname']))
    aos_allnodes = {k: aos_allnodes[k] for k in order_nodes}
    
    print(f"De volgende nodes zitten in deze blueprint:")
    for node in aos_allnodes:
        print(aos_allnodes[node]["hostname"])

    use_radius = input('Account ' + username + ' gebruiken om in te loggen op de node (y/n)? ')
    if use_radius == 'y':
        node_username = username
        node_password = password
    print("'multi-execute' to execute")
    print("'multi-break' to exit")
    print("'multi-show' to show commands")
    print("")
    multi_ssh_command = []
    while True:
        multi_ssh_singleline = input('Command: ')
        if multi_ssh_singleline == 'multi-execute':
            for node in aos_allnodes:
                if use_radius == 'n':
                    print("------------------------------------------")
                    print(aos_allnodes[node]['hostname'])
                    node_username = input('Username: ')
                    node_password = getpass.getpass('Password: ')
                node_ssh = ssh_login(node_username, node_password, aos_allnodes[node]["mgmt_ip"])
                ssh_multi(node_ssh, multi_ssh_command)
            print(f"Done")
        elif multi_ssh_singleline == 'multi-break':
            exit()       
        elif multi_ssh_singleline == 'multi-show':
            print(multi_ssh_command)
        else:
            multi_ssh_command.append(multi_ssh_singleline)

elif choice == '0':
    exit()
