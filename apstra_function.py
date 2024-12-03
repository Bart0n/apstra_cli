import requests
import sys
import json
import time
import paramiko
import getpass
import secrets
import string
import random
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def apstra_authenticate(aos_server, username, password):
    url = 'https://' + aos_server + '/api/user/login'
    headers = { 'Content-Type':"application/json", 'Cache-Control':"no-cache" }
    data = '{ \"username\":\"' + username + '\", \"password\":\"' + password + '\" }'
    response = requests.request("POST", url, data=data, headers=headers, verify=False)
    if response.status_code != 201:
        sys.exit('Error: Authentication Failed')
    else:
        print("Successfully authenticated")
    auth_token = response.json()['token']
    headers = { 'AuthToken':auth_token, 'Content-Type':"application/json", 'Accept':"application/json" ,'Cache-Control':"no-cache" }
    return headers

def apstra_getblueprints(aos_server, aos_auth):
    url = 'https://' + aos_server + '/api/blueprints'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    blueprints = response.json()
    blueprints = blueprints['items']
    print("Aanwezige blueprints:")
    for i in blueprints:
        print (i['label'])
    dc = input('In welke blueprint wil je een aanpassing maken? ')
    try:
        dc = next(item for item in blueprints if item["label"] == dc)
    except:
        sys.exit('Niet bestaande blueprint opgegeven, exiting')
    return dc

def apstra_getsecurityzone(aos_server, aos_auth, aos_blueprint):
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/security-zones'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    sz = response.json()
    sz = sz['items']
    sz_dict = {}
    for id, info in sz.items():
        sz_dict[info['label']]=id
    print('Aanwezige nodes:')
    print('\n'.join(sz_dict))
    selected_sz= input ('Welke security zone wil je aanpassen? ')
    try:
        sz_id = sz_dict[selected_sz]
    except:
        sys.exit('Niet bestaande sz opgegeven, exiting')
    return sz_id, selected_sz, sz[sz_id]["routing_policy_id"]

def apstra_updatesecurityzone(aos_server, aos_auth, aos_blueprint, aos_sz_id, new_sz_name, aos_sz_routing_policy_id):
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/security-zones/' + aos_sz_id
    payload = json.dumps({"label":new_sz_name, "vrf_name":new_sz_name, "routing_policy_id":aos_sz_routing_policy_id})
    response = requests.patch(url, headers=aos_auth, data=payload, verify=False)

def apstra_commit(aos_server, aos_auth, aos_blueprint, commit_description):
    time.sleep(1)
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/diff-status/'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    diffstatus = response.json()
    staging_ver = diffstatus["staging_version"]
    deployment_ver = diffstatus["deployed_version"]
    if staging_ver == deployment_ver:
        sys.exit('Geen veranderingen in blueprint gevonden. Exiting.')
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/deploy/'
    payload = json.dumps({"version":staging_ver, "description":commit_description})
    response = requests.request('PUT', url, headers=aos_auth, data=payload, verify=False)  

def apstra_drain(aos_server, aos_auth, aos_blueprint, aos_node_id, aos_node_sn):
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/nodes/' + aos_node_id
    payload = json.dumps({"deploy_mode":"drain", "system_id":aos_node_sn})
    response = requests.patch(url, headers=aos_auth, data=payload, verify=False)
    time.sleep(1)

def apstra_undeploy(aos_server, aos_auth, aos_blueprint, aos_node_id):
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/nodes/' + aos_node_id
    payload = json.dumps({"deploy_mode":"undeploy", "system_id":None})
    response = requests.patch(url, headers=aos_auth, data=payload, verify=False)
    time.sleep(1)

def apstra_deploy(aos_server, aos_auth, aos_blueprint, aos_node_id, aos_node_sn):
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/nodes/' + aos_node_id
    payload = json.dumps({"deploy_mode":"deploy", "system_id":aos_node_sn})
    response = requests.patch(url, headers=aos_auth, data=payload, verify=False)
    time.sleep(1)

def apstra_getnode(aos_server, aos_auth, aos_blueprint):
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/nodes?node_type=system'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    nodes = response.json()
    nodes = nodes['nodes']
    nodes_dict = {}
    for node_id, node_info in nodes.items():
        if node_info['system_type'] == 'switch' and node_info['role'] != 'remote_gateway':
            nodes_dict[node_info['label']]= node_id
    nodes_dict = dict(sorted(nodes_dict.items()))
    print('Aanwezige nodes:')
    print('\n'.join(nodes_dict))
    selected_node = input ('Welke node wil je aanpassen? ')
    try:
        node_key = nodes_dict[selected_node]
        node_sn = nodes[node_key]["system_id"]
    except:
        sys.exit('Niet bestaande node  opgegeven, exiting')

    #Get Node IP
    url = 'https://' + aos_server + '/api/systems/' + node_sn
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    node_ip = response.json()
    node_ip = node_ip["facts"]["mgmt_ipaddr"]

    #Get Agent ID for that node
    url = 'https://' + aos_server + '/api/system-agents'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    sys_agents = response.json()
    sys_agents = sys_agents['items']
    sys_agents_dict = {}
    for i in sys_agents:
        sys_agents_dict[i['config']['management_ip']]= i['config']['id']
    
    returnlist=[node_key, selected_node, node_sn, node_ip, sys_agents_dict[node_ip]]
    return returnlist

def apstra_changeagent(aos_server, aos_auth, aos_node_agentid, apstra_password):
    url = 'https://' + aos_server + '/api/system-agents/' + aos_node_agentid
    payload = json.dumps({"password":apstra_password})
    response = requests.patch(url, headers=aos_auth, data=payload, verify=False)
    print("Offbox Agent in Apstra aangepast. Sleeping for 5 seconds...")
    time.sleep(5)

    #Check agent
    url = 'https://' + aos_server + '/api/system-agents/' + aos_node_agentid + '/check'
    response = requests.request('POST', url, headers=aos_auth, verify=False)
    print('Verzoek om de agent te checken verstuurd. Sleeping for 30 secondes ...')
    time.sleep(30)

    #Check job
    url = 'https://' + aos_server + '/api/system-agents/' + aos_node_agentid + '/job-history'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    sys_agents_lastjob = response.json()
    if sys_agents_lastjob['items'][0]['job_type'] == 'check' and sys_agents_lastjob['items'][0]['state'] == 'success':
        print("Check succesvol")
    else:
        print("Er is iets fout gegaan tijdens de 'check' fase. Controlleer handmatig in Apstra! Details:")
        sys.exit(sys_agents_lastjob['items'][0])

    #Retrieve Pristine Config
    url = 'https://' + aos_server + '/api/system-agents/' + aos_node_agentid + '/collect-pristine'
    response = requests.request('POST', url, headers=aos_auth, verify=False)
    print('Verzoek om de pristine config op te halen verstuurd. Sleeping for 30 secondes ...')
    time.sleep(30)

    #Check job
    url = 'https://' + aos_server + '/api/system-agents/' + aos_node_agentid + '/job-history'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    sys_agents_lastjob = response.json()
    if sys_agents_lastjob['items'][0]['job_type'] == 'collectPristine' and sys_agents_lastjob['items'][0]['state'] == 'success':
        print("Pristine config succesvol opgehaald")
    else:
        print("Er is iets fout gegaan tijdens de 'collect pristine' fase. Controlleer handmatig in Apstra! Details:")
        sys.exit(sys_agents_lastjob['items'][0])

def apstra_changepassword(aos_server, aos_auth, aos_blueprint, aos_node, node_ssh, pw_apstra_mgr, pw_root):
    apstra_drain(aos_server, aos_auth, aos_blueprint, aos_node[0], aos_node[2])
    commit_description= f"Automation: Set {aos_node[1]} to drain for password change"
    apstra_commit(aos_server, aos_auth, aos_blueprint, commit_description)
    print(f'{aos_node[1]} drained. Sleeping for 60 seconds...')
    time.sleep(60)
    apstra_undeploy(aos_server, aos_auth, aos_blueprint, aos_node[0])
    commit_description= f"Automation: Removed {aos_node[1]} from blueprint for password change"
    apstra_commit(aos_server, aos_auth, aos_blueprint, commit_description)
    print(f'{aos_node[1]} undeployed. Sleeping for 30 seconds...')
    time.sleep(30)
    ssh_changepw(node_ssh, pw_apstra_mgr, pw_root)
    apstra_changeagent(aos_server, aos_auth, aos_node[4], pw_apstra_mgr)
    apstra_deploy(aos_server, aos_auth, aos_blueprint, aos_node[0], aos_node[2])
    commit_description= f"Automation: Set {aos_node[1]} to deploy after password change"
    apstra_commit(aos_server, aos_auth, aos_blueprint, commit_description)
    print(f'{aos_node[1]} deployed! :)')

def apstra_getallnodes(aos_server, aos_auth, aos_blueprint):
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/nodes?node_type=system'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    nodes = response.json()
    nodes = nodes['nodes']
    nodes = {key:val for key, val in nodes.items() if (val["system_type"] == 'switch' and val["role"] != "remote_gateway" and val['system_id'] != None)}
    #aos_node[1]=Hostname [1]=NodeID [2]=NodeSN [3]=Node MGT IP [4]=AgentID
    removelist =["port_channel_id_max", "system_index", "tags", "access_l3_peer_link_port_channel_id_max", "system_type","deploy_mode","port_channel_id_min" ,"position_data", "property_set", "group_label", "label", "access_l3_peer_link_port_channel_id_min", "role", "management_level", "type", "external"]
    remove_nested_keys(nodes, removelist)

    # #Get Nodes IP and Agent ID and set wait peroid after deployment (higher for BRD and SPS)
    for node in nodes:
        url = 'https://' + aos_server + '/api/systems/' + nodes[node]["system_id"]
        response = requests.request('GET', url, headers=aos_auth, verify=False)
        node_ip = response.json()
        nodes[node]["mgmt_ip"] = node_ip["facts"]["mgmt_ipaddr"]

        url = 'https://' + aos_server + '/api/system-agents'
        response = requests.request('GET', url, headers=aos_auth, verify=False)
        sys_agents = response.json()
        sys_agents = sys_agents['items']
        sys_agents_dict = {}
        for i in sys_agents:
            sys_agents_dict[i['config']['management_ip']]= i['config']['id']
        nodes[node]["agent_id"] = sys_agents_dict[nodes[node]["mgmt_ip"]]
        
        if ("BRD" or "BORDER" or "SPS" or "SPINE") in nodes[node]["hostname"]:
            nodes[node]["sleep"]=300
        else:
            nodes[node]["sleep"]=60

    return nodes

def apstra_getactualanomaly(aos_server, aos_auth, aos_blueprint):
    time.sleep(5)
    url = 'https://' + aos_server + '/api/blueprints/' + aos_blueprint["id"] + '/anomalies_services_count'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    bp_anomolies_bgp = response.json()
    bp_anomolies_bgp = next((item for item in bp_anomolies_bgp['items'] if item["type"] == "bgp"), {'type': 'bgp', 'role': 'spine_leaf', 'count': 0})
    return bp_anomolies_bgp

def apstra_changeallpassword(aos_server, aos_auth, aos_blueprint, aos_node, node_ssh):
    apstra_drain(aos_server, aos_auth, aos_blueprint, aos_node["id"], aos_node["system_id"])
    commit_description= f"Automation: Set {aos_node['hostname']} to drain for password change"
    apstra_commit(aos_server, aos_auth, aos_blueprint, commit_description)
    time.sleep(1)
    print(f'{aos_node["hostname"]} drained.')
    blueprints_anomolies = apstra_getactualanomaly(aos_server, aos_auth, aos_blueprint)
    while blueprints_anomolies['count'] > aos_blueprint['anomaly_counts']['bgp']:
        blueprints_anomolies = apstra_getactualanomaly(aos_server, aos_auth, aos_blueprint)            
    apstra_undeploy(aos_server, aos_auth, aos_blueprint, aos_node["id"])
    commit_description= f"Automation: Removed {aos_node['hostname']} from blueprint for password change"
    apstra_commit(aos_server, aos_auth, aos_blueprint, commit_description)
    print(f'{aos_node["hostname"]} undeployed.')
    time.sleep(30)
    ssh_changepw(node_ssh, aos_node["pw_apstra_mgr"], aos_node["pw_root"])
    print(f"New PW apstra_mgr:")
    print(aos_node["pw_apstra_mgr"])
    print(f"New password root:")
    print(aos_node["pw_root"])
    apstra_changeagent(aos_server, aos_auth, aos_node["agent_id"], aos_node["pw_apstra_mgr"])
    apstra_deploy(aos_server, aos_auth, aos_blueprint, aos_node["id"], aos_node["system_id"])
    commit_description= f"Automation: Set {aos_node['hostname']} to deploy after password change"
    apstra_commit(aos_server, aos_auth, aos_blueprint, commit_description)
    print(f'{aos_node["hostname"]} deployed! :) (Waiting for device to be operational)')
    time.sleep(1)
    blueprints_anomolies = apstra_getactualanomaly(aos_server, aos_auth, aos_blueprint)
    while blueprints_anomolies['count'] > aos_blueprint['anomaly_counts']['bgp']:
        blueprints_anomolies = apstra_getactualanomaly(aos_server, aos_auth, aos_blueprint)        

def apstra_seachconfiglet(aos_server, aos_auth, search_item):
    url = 'https://' + aos_server + '/api/design/configlets'
    response = requests.request('GET', url, headers=aos_auth, verify=False)
    configlet_global = response.json()
    configlet_global = configlet_global['items']
    #search_item = input("Zoek in alle configlets naar: ")
    search_result = []
    for i in range(len(configlet_global)):
        if search_item in configlet_global[i]["generators"][0]["template_text"]:
            search_result.append(i)
    return configlet_global, search_result    

def apstra_changeconfiglet(aos_server, aos_auth, configlet_global, search_result, search_item, replacewith):
    for i in search_result:
        replaced_template_text = configlet_global[i]["generators"][0]["template_text"].replace(search_item, replacewith)
        url = 'https://' + aos_server + '/api/design/configlets/'+configlet_global[i]["id"]
        payload = json.dumps({"ref_archs":["two_stage_l3clos"],"generators":[{"config_style":"junos","section":"set_based_system","template_text":replaced_template_text}],"id":configlet_global[i]["id"],"display_name":configlet_global[i]["display_name"]})
        response = requests.request('PUT', url, headers=aos_auth, data=payload, verify=False)

def ssh_login(username, password, node_ip):
    try:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(node_ip, port=22, username=username, password=password, banner_timeout=200)
        time.sleep(1)
        connection = client.invoke_shell()
        connection.send('\n')
        time.sleep(1)
    except Exception as err:
        print("Error bij het inloggen via SSH. Melding:")
        sys.exit(str(err))
    return connection

def ssh_changepw(connection, apstra_password, root_password):
    try:
        connection.send('configure \n')
        time.sleep(1)
        connection.send('set system login user apstra_mgr authentication plain-text-password-value ' + apstra_password + '\n')
        time.sleep(1)
        connection.send('set system root-authentication plain-text-password-value ' + root_password + '\n')
        time.sleep(1)
        connection.send('commit and-quit \n')
        time.sleep(3)
        print("Password is aangepast op de node.")
    except Exception as err:
        print("Error bij het uitvoeren van de SSH commando's. Melding:")
        print(str(err))

def ssh_multi(connection, command):
    try:
        for line in command:
            connection.send(line + ' \n')
            time.sleep(0.5)
    except Exception as err:
        print("Error bij het uitvoeren van de SSH commando's. Melding:")
        print(str(err))

def generate_pw():
    secret_password = ''.join((secrets.choice(string.ascii_letters + string.digits) for i in range(random.randint(22, 32)))) + ''.join((secrets.choice(string.ascii_uppercase) for i in range(random.randint(2, 8)))) + ''.join((secrets.choice(string.digits) for i in range(random.randint(2, 8)))) + ''.join('!@#$%^*.,' for i in range (random.randint(1,2)))
    secret_password = ''.join(random.sample(secret_password,len(secret_password)))
    return secret_password

def remove_nested_keys(dictionary, keys_to_remove):
    for key in keys_to_remove:
        if key in dictionary:
            del dictionary[key]

    for value in dictionary.values():
        if isinstance(value, dict):
            remove_nested_keys(value, keys_to_remove)

    return dictionary
