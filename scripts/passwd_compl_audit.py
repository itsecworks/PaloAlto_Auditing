#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the security rules and the security profile settings within panorama device-group hierarchy.
#
import xml.etree.ElementTree as ET
import time
import os

file_path = 'C:/Users/dakos/Downloads/Panorama_Config_Bundle/Panorama_20231214/'
xml_input = file_path + 'prismapan_000710014322.xml'
#xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")

dict_xpath = {
  "pwd_complexity": {
    "fw": "./mgt-config/password-complexity/",
    "pan": "./config/mgt-config/password-complexity/"
  },
  "admin_lockout": {
    "fw": "./devices/entry/deviceconfig/setting/management/admin-lockout/",
    "pan": "./config/devices/entry/deviceconfig/setting/management/admin-lockout/"
  }
}
fw_xpath = dict_xpath["admin_lockout"]["fw"]
pan_xpath = dict_xpath["admin_lockout"]["pan"]
result_output = file_path + 'admin_lockout_' + time_str + '.csv'

def get_xml_files(path):
    xml_list = []
    for filename in os.listdir(path):
        if filename.endswith(".xml"):
            xml_list.append(os.path.join(path, filename))
    return xml_list

files = get_xml_files(file_path)

pwd_complexity_dict = {"panorama-templates": {}, "firewalls": {}}
pwd_compl_header_list = []
for xml_input in files:
    if os.path.getsize(xml_input) > 0:
        tree = ET.parse(xml_input)
        root = tree.getroot()
        if root.find("./panorama"):
            print('its a panorama config.....................................')
            for tmpl in root.findall("./devices/entry/template/entry"):
                tmpl_name = tmpl.attrib["name"]
                if tmpl_name not in pwd_complexity_dict["panorama-templates"]:
                    pwd_complexity_dict["panorama-templates"][tmpl_name] = {}
                for element in tmpl.findall(pan_xpath):
                    if element.tag not in pwd_compl_header_list:
                        pwd_compl_header_list.append(element.tag)
                    for tmpl2 in root.findall("./devices/entry/template/entry"):
                        tmpl2_name = tmpl2.attrib["name"]
                        if tmpl2_name not in pwd_complexity_dict["panorama-templates"]:
                            pwd_complexity_dict["panorama-templates"][tmpl2_name] = {}
                        if pwd_complexity_dict["panorama-templates"][tmpl2_name].get(element.tag) is None:
                            pwd_complexity_dict["panorama-templates"][tmpl2_name][element.tag] = "not_set"

                    if element.text:
                        pwd_complexity_dict["panorama-templates"][tmpl_name][element.tag] = element.text
                    else:
                        pwd_complexity_dict["panorama-templates"][tmpl_name][element.tag] = "not_set"


        else:
            print('its a firewall config')
            hostname = root.find("./devices/entry/deviceconfig/system/hostname").text
            if hostname not in pwd_complexity_dict["firewalls"]:
                pwd_complexity_dict["firewalls"][hostname] = {}
            for element in root.findall(fw_xpath):
                if element.tag not in pwd_compl_header_list:
                    pwd_compl_header_list.append(element.tag)
                if element.text:
                    pwd_complexity_dict["firewalls"][hostname][element.tag] = element.text
                else:
                    pwd_complexity_dict["firewalls"][hostname][element.tag] = "not_set"

if len(pwd_complexity_dict["firewalls"]) > 0:
    for entry in pwd_compl_header_list:
        for fw in pwd_complexity_dict["firewalls"]:
            if pwd_complexity_dict["firewalls"][fw].get(entry) is None:
                pwd_complexity_dict["firewalls"][fw][entry] = "not_set"

result = ''

first_tmpl = list(pwd_complexity_dict["panorama-templates"].keys())[0]
headerlist = ['type','name']
for element in sorted(pwd_complexity_dict["panorama-templates"][first_tmpl]):
    headerlist.append(element)
result += ','.join(headerlist) + '\n'

for key in pwd_complexity_dict:
    for name in pwd_complexity_dict[key]:
        mylist = [key, name]
        for element in sorted(pwd_complexity_dict[key][name]):
            mylist.append(str(pwd_complexity_dict[key][name][element]))
        result += ','.join(mylist) + '\n'

    with open(result_output, 'w') as fp:
        fp.write(result)