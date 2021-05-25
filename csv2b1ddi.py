#!/usr/bin/env python
"""
Version 0.6:
- Added support for Authoritative zones and DNS objects, make sure DNS view in CSV has correct name
Version 0.5:
- Added support for fixed addresses, reservations and dhcp ranges
Version 0.4:
- Added support for Network Containers (Address Blocks) and Comments
Version 0.3:
- Added support for HA groups
Version 0.2:
- Added override for imported DHCP options so they are applied
- Added functionality to apply DHCP server (dhcp/host) to subnet

ToDo:
- Add missing DHCP options
- Split global CSV and provide functions per object type
- Add support for tags
- Add support for Exclusion Ranges
- Add support for Hosts
- Add error checking
"""

import csv, sys, bloxone, argparse, ipaddress, re, json

# Parse CLI arguments and provide help and version information
parser = argparse.ArgumentParser(description='This is a simple NIOS to B1DDI migration tool', prog='csv2b1ddi')
parser.add_argument('-b', '--networkblock', action="store", dest="networkcontainers", help="CSV file with Networks data")
parser.add_argument('-n', '--networks', action="store", dest="networks", help="CSV file with Networks data")
parser.add_argument('-r', '--ranges', action="store", dest="ranges", help="CSV file with DHCP ranges data")
parser.add_argument('-f', '--fixed', action="store", dest="fixed", help="CSV file with Fixed Address data")
parser.add_argument('-z', '--authzone', action="store", dest="authzones", help="CSV file with Authoritative Zones data")
parser.add_argument('-a', '--arecord', action="store", dest="arecord", help="CSV file with A record data")
parser.add_argument('-t', '--txtrecord', action="store", dest="txtrecord", help="CSV file with TXT record data")
parser.add_argument('-m', '--mxrecord', action="store", dest="mxrecord", help="CSV file with MX record data")
parser.add_argument('-p', '--ptrrecord', action="store", dest="ptrrecord", help="CSV file with PTR record data")
parser.add_argument('-s', '--srvrecord', action="store", dest="srvrecord", help="CSV file with SRV record data")
parser.add_argument('--aaaa', action="store", dest="aaaarecord", help="CSV file with AAAA record data")
parser.add_argument('--cname', action="store", dest="cnamerecord", help="CSV file with AAAA record data")
parser.add_argument('--tags', action="store", dest="tags", help="Tags to apply to imported objects")
parser.add_argument('-i', '--ipspace', action="store", dest="ipspace", help="Name of IP space to import data in", required=True)
parser.add_argument('-c', '--config', action="store", dest="config", help="Path to ini file with API key", required=True)
parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.3')
options = parser.parse_args()

# Parse the API options including URL, version and API key
b1ddi = bloxone.b1ddi(options.config)

# Get the IP space that we will import data in (Network View)
ipspacePath = b1ddi.get_id('/ipam/ip_space', key="name", value=options.ipspace, include_path=True)
print('The IP space used is ' + options.ipspace + ' with the following path: ' + ipspacePath)

if options.tags:
    tags = '"tags":' + options.tags
else:
    tags = '"tags":{""}'

jsonTags = json.loads(json.dumps(tags))

# Create and populate dictionary containing DHCP Option Codes
optionDict = {}
optioncodes = b1ddi.get('/dhcp/option_code', _fields='code,id')
jsonOptioncodes = optioncodes.json()['results']
for item in jsonOptioncodes:
    code = item['code']
    id = item['id']
    optionDict.update( {code:id} )

# Create and populate dictionary containing DHCP Hosts (Servers)
dhcphostDict = {}
dhcphosts = b1ddi.get('/dhcp/host', _fields='name,id')
hagroup = b1ddi.get('/dhcp/ha_group', _fields='name,id')
jsonDhcphosts = dhcphosts.json()['results']
jsonHagroup = hagroup.json()['results']
for item in jsonDhcphosts:
    name = item['name']
    id = item['id']
    dhcphostDict.update({name: id})

def dnsserverDict():
    dnsservers = {}
    dnshosts = b1ddi.get('/dns/host', _fields='name,id')
    jsonDnshosts = dnshosts.json()['results']
    for item in jsonDnshosts:
        name = item['name']
        id = item['id']
        dnsservers.update({name: id})
    return dnsservers

# Defition for DHCP Hosts and HA Groups to dictionary for lookup
def dhcpserverDict():
    dhcpservers = {}
    dhcphosts = b1ddi.get('/dhcp/host', _fields='name,id')
    hagroup = b1ddi.get('/dhcp/ha_group', _fields='name,id')
    listDhcphosts = dhcphosts.json()['results']
    listHagroups = hagroup.json()['results']
    serversList = listDhcphosts + listHagroups
    for item in serversList:
        name = item['name']
        id = item['id']
        dhcpservers.update({name: id})
    return dhcpservers

# Definition for finding DHCP host ID from dictionary
def getDhcphostid(name):
    try:
        dhcphostID = dhcpservers[name] # Try to find a DHCP Host with name from CSV
    except KeyError:
        dhcphostID = '' # If DHCP Host is not found, leave it empty
    return dhcphostID

def getDnshostid(name):
    try:
        dnshostID = dnsservers[name] # Try to find a DHCP Host with name from CSV
    except KeyError:
        dnshostID = '' # If DHCP Host is not found, leave it empty
    return dnshostID

# Definition for importing CSV and saving it to a dictionary with key, value pairs
def csv_dict_list(csvfile):
    reader = csv.DictReader(open(csvfile, 'r'))
    dict_list = []
    for line in reader:
        dict_list.append(line)
    return dict_list

# Definition for getting DHCP options and putting them in right JSON format
def getDhcpoptions(csvline):
    dhcpoptions = {optionDict[15]: csvline['domain_name'], optionDict[6]: csvline['domain_name_servers'], optionDict[3]: csvline['routers']}  # Get DHCP options for values referenced by a name instead of OPTION-XX and save in dictionary
    for keys in csvline.keys():
        if re.match('^OPTION-DHCP-(?<!\d)(?:[1-9]?\d|1\d\d|2(?:[0-4]\d|5[0-5]))(?!\d)', keys):  # Search for DHCP options in the format OPTION-XXX
            code = (re.findall('\d+', keys))  # Extract the DHCP option number
            codeInteger = int(code[0])  # Convert the DHCP option number to a integer value
            print(csvline[keys])
            dhcpoptions.update({optionDict[codeInteger]: csvline[keys]})  # Add the DHCP code integer and value to the dhcpoptions dictionary
    nonemptydhcpoptions = {k: v for k, v in dhcpoptions.items() if v}  # Remove key/value pairs from DHCP options if value is empty
    dhcpoptionlist = []  # Create empty list to populate with options
    for key in nonemptydhcpoptions:
        dhcpoptionlist.append({"type": "option", "option_code": key, "option_value": nonemptydhcpoptions[key]})  # Append DHCP Options to list when options are not empty
    jsonOptions = json.dumps(dhcpoptionlist)  # Convert DHCP Options list to JSON
    return jsonOptions

dhcpservers = dhcpserverDict()
dnsservers = dnsserverDict()

# Import NIOS CSV for networkcontainers
def addcontainers(networkcontainers):
    for item in networkcontainers:
        cidr = item['netmask*']
        address = item['address*'] # Put network address in variable
        comment = item['comment']
        body = ('{"space":"' + ipspacePath + '","address":"' + address + '","cidr":' + cidr + ',"comment":"' + comment + '",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(json.dumps(body)) # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/ipam/address_block', body=jsonBody) # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

# Import NIOS CSV for network
def addnetworks(networks):
    for item in networks:
        cidr = str(ipaddress.ip_network('0.0.0.0/' + item['netmask*']).prefixlen) # Convert netmask to CIDR
        address = item['address*'] # Put network address in variable
        comment = item['comment']
        dhcphostID = getDhcphostid(item['dhcp_members']) # Get DHCP Host ID
        jsonDhcpoptions = getDhcpoptions(item) # Get DHCP Options in JSON
        body = ('{"space":"' + ipspacePath + '","address":"' + address + '","cidr":' + cidr + ',"dhcp_host":"' + dhcphostID + '","comment":"' + comment + '","dhcp_options":' + jsonDhcpoptions + ',' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(json.dumps(body)) # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/ipam/subnet', body=jsonBody) # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addranges(ranges):
    for item in ranges:
        start = item['start_address*']
        end = item['end_address*']
        comment = item['comment']
        body = ('{"space":"' + ipspacePath + '","start":"' + start + '","end":"' + end + '","comment":"' + comment + '",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(json.dumps(body)) # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/ipam/range', body=jsonBody) # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addfixed(fixed):
    for item in fixed:
        address = item['ip_address*']
        comment = item['comment']
        match_type = item['match_option']
        match_value = item['mac_address']
        name = item['name']
        if match_type == 'RESERVED':
            body = ('{"space":"' + ipspacePath + '","address":"' + address + '","comment":"' + comment + '",' + jsonTags + '}')  # Create body for network creation
            print(body)
            jsonBody = json.loads(json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
            response = b1ddi.create('/ipam/address', body=jsonBody)  # Create network using BloxOne API
            if response.status_code in b1ddi.return_codes_ok:
                print(response.text)
            else:
                print(response.status_code)
                print(response.text)
        elif match_type == 'MAC_ADDRESS':
            body = ('{"ip_space":"' + ipspacePath + '","address":"' + address + '","match_type":"mac","match_value":"' + match_value +'","comment":"' + comment + '",' + jsonTags + '}')  # Create body for network creation
            print(body)
            jsonBody = json.loads(json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
            response = b1ddi.create('/dhcp/fixed_address', body=jsonBody)  # Create network using BloxOne API
            if response.status_code in b1ddi.return_codes_ok:
                print(response.text)
            else:
                print(response.status_code)
                print(response.text)

def addzones(authzones):
    for item in authzones:
        nsgroup = b1ddi.get_id('/dns/auth_nsg',key="name",value=item['ns_group'],include_path=True)
        fqdn = item['fqdn*']
        comment = item['comment']
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        body = ('{"view":"' + view + '","fqdn":"' + fqdn + '","nsgs":["' + nsgroup + '"],"comment":"' + comment + '","primary_type":"cloud",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/auth_zone', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addarecord(arecord):
    for item in arecord:
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        fqdn = item['fqdn*']
        address = item['address*']
        comment = item['comment']
        body = ('{"view":"' + view + '","absolute_name_spec":"' + fqdn + '","rdata":{"address":"' + address + '"},"comment":"' + comment + '","type":"A",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(
            json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/record', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addaaaarecord(aaaarecord):
    for item in aaaarecord:
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        fqdn = item['fqdn*']
        address = item['address*']
        comment = item['comment']
        body = ('{"view":"' + view + '","absolute_name_spec":"' + fqdn + '","rdata":{"address":"' + address + '"},"comment":"' + comment + '","type":"AAAA",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(
            json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/record', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addtxtrecord(txtrecord):
    for item in txtrecord:
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        fqdn = item['fqdn*']
        text = item['text*']
        comment = item['comment']
        body = ('{"view":"' + view + '","absolute_name_spec":"' + fqdn + '","rdata":{"text":"' + text + '"},"comment":"' + comment + '","type":"TXT",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(
            json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/record', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addsrvrecord(srvrecord):
    for item in srvrecord:
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        fqdn = item['fqdn*']
        port = item['port*']
        priority = item['priority*']
        target = item['target*']
        weight = item['weight*']
        comment = item['comment']
        body = ('{"view":"' + view + '","absolute_name_spec":"' + fqdn + '","rdata":{"port":' + port + ',"priority":' + priority + ',"target":"' + target + '","weight":' + weight +'},"comment":"' + comment + '","type":"SRV",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(
            json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/record', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addmxrecord(mxrecord):
    for item in mxrecord:
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        fqdn = item['fqdn*']
        exchange = item['mx*']
        preference = item['priority*']
        comment = item['comment']
        body = ('{"view":"' + view + '","absolute_name_spec":"' + fqdn + '","rdata":{"exchange":"' + exchange + '","preference":' + preference + '},"comment":"' + comment + '","type":"MX",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(
            json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/record', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addcnamerecord(cnamerecord):
    for item in cnamerecord:
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        fqdn = item['fqdn*']
        cname = item['canonical_name']
        comment = item['comment']
        body = ('{"view":"' + view + '","absolute_name_spec":"' + fqdn + '","rdata":{"cname":"' + cname + '"},"comment":"' + comment + '","type":"CNAME",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(
            json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/record', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def addptrrecord(ptrrecord):
    for item in ptrrecord:
        view = b1ddi.get_id('/dns/view', key="name",value=item['view'], include_path=True)
        fqdn = item['fqdn']
        dname = item['dname*']
        comment = item['comment']
        body = ('{"view":"' + view + '","absolute_name_spec":"' + fqdn + '","rdata":{"dname":"' + dname + '"},"comment":"' + comment + '","type":"PTR",' + jsonTags + '}')  # Create body for network creation
        jsonBody = json.loads(
            json.dumps(body))  # Convert body to correct JSON and ensure quotes " are not escaped (ex. \")
        response = b1ddi.create('/dns/record', body=jsonBody)  # Create network using BloxOne API
        if response.status_code in b1ddi.return_codes_ok:
            print(response.text)
        else:
            print(response.status_code)
            print(response.text)

def checkcsv():
    if options.networkcontainers is not None:
        networkcontainers = csv_dict_list(options.networkcontainers)
        addcontainers(networkcontainers)
    if options.networks is not None:
        networks = csv_dict_list(options.networks)
        addnetworks(networks)
    if options.ranges is not None:
        ranges = csv_dict_list(options.ranges)
        addranges(ranges)
    if options.fixed is not None:
        fixed = csv_dict_list(options.fixed)
        addfixed(fixed)
    if options.authzones is not None:
        authzones = csv_dict_list(options.authzones)
        addzones(authzones)
    if options.arecord is not None:
        arecord = csv_dict_list(options.arecord)
        addarecord(arecord)
    if options.txtrecord is not None:
        txtrecord = csv_dict_list(options.txtrecord)
        addtxtrecord(txtrecord)
    if options.mxrecord is not None:
        mxrecord = csv_dict_list(options.mxrecord)
        addmxrecord(mxrecord)
    if options.ptrrecord is not None:
        ptrrecord = csv_dict_list(options.ptrrecord)
        addptrrecord(ptrrecord)
    if options.srvrecord is not None:
        srvrecord = csv_dict_list(options.srvrecord)
        addsrvrecord(srvrecord)
    if options.aaaarecord is not None:
        aaaarecord = csv_dict_list(options.aaaarecord)
        addaaaarecord(aaaarecord)
    if options.cnamerecord is not None:
        cnamerecord = csv_dict_list(options.cnamerecord)
        addcnamerecord(cnamerecord)
    print('Finished processing all CSV files')

checkcsv()
