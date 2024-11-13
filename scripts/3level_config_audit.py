#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script finds the password complexity settings from the config bundle and reports on that.
#
import pdb
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, ElementTree
import time
import os


def get_xml_files(path):
    xml_list = []
    for filename in os.listdir(path):
        if filename.endswith(".xml"):
            xml_list.append(os.path.join(path, filename))
    return xml_list


def getname(element: Element) -> str:

    if element.attrib is not None and "name" in element.attrib:
        element_name: str = element.attrib["name"]
    else:
        element_name = element.text
    return element_name


def xml_to_line(xml_data: Element, element_dict: dict = None, element_line: str = None):

    if element_dict is None:
        element_dict = {}
    if element_line is None:
        element_line = ''

    for element in xml_data:
        if len(element) > 0:
            if element.tag == "entry":
                tag_name = element.attrib["name"]
            else:
                tag_name = element.tag
            if element.tag == "scan-white-list":
                for entry in element:
                    print(entry.attrib["name"])
                    print(entry.find("./ipv4").text)
            if element.tag != "phash":
                element_line_new = element_line + "_" + tag_name
                element_dict = xml_to_line(element, element_dict, element_line_new)
        else:
            if element.tag != "phash":
                element_line_final = element_line + "_" + element.tag
                element_dict[element_line_final] = element.text
    return element_dict


file_path = 'C:/Users/test/Downloads/Panorama_20241025/'
time_str = time.strftime("%Y%m%d_%H%M%S")
config_key = "users"
result_output = file_path + config_key + '_' + time_str + '.csv'

dict_xpath = {
  "device-telemetry": {
      "fw": "./devices/entry/deviceconfig/system/device-telemetry",
      "pan": "./config/devices/entry/deviceconfig/system/device-telemetry"
  },
  "admin_lockout": {
    "fw": "./devices/entry/deviceconfig/setting/management/admin-lockout/",
    "pan": "./config/devices/entry/deviceconfig/setting/management/admin-lockout/"
  },
  "login_banner": {
      "fw": "./devices/entry/deviceconfig/system/login-banner",
      "pan": "./config/devices/entry/deviceconfig/system/login-banner"
  },
  "update-schedule_anti-virus": {
      "fw": "./devices/entry/deviceconfig/system/update-schedule/anti-virus",
      "pan": "./config/devices/entry/deviceconfig/system/update-schedule/anti-virus"
  },
  "update-schedule_threats": {
      "fw": "./devices/entry/deviceconfig/system/update-schedule/threats",
      "pan": "./config/devices/entry/deviceconfig/system/update-schedule/threats"
  },
  "update-schedule_wildfire": {
      "fw": "./devices/entry/deviceconfig/system/update-schedule/wildfire",
      "pan": "./config/devices/entry/deviceconfig/system/update-schedule/wildfire"
  },
  "password_complexity": {
      "fw": "./config/mgt-config/password-complexity",
      "pan": "./config/mgt-config/password-complexity"
  },
  "users": {
      "fw": "./config/mgt-config/users",
      "pan": "./config/mgt-config/users"
  },
  "zone-protection-profile": {
      "fw": "./devices/entry/network/profiles/zone-protection-profile/entry",
      "pan": "./config/devices/entry/network/profiles/zone-protection-profile/entry"
  },
  "authentication-profile": {
      "fw": "./devices/entry/deviceconfig/system/authentication-profile",
      "pan": "./config/devices/entry/deviceconfig/system/authentication-profile"
  },
  "timezone": {
        "fw": "./devices/entry/deviceconfig/system/timezone",
        "pan": "./config/devices/entry/deviceconfig/system/timezone"
  },
  "domain": {
      "fw": "./devices/entry/deviceconfig/system/domain",
      "pan": "./config/devices/entry/deviceconfig/system/domain"
  },
  "log_syslog_AZURE_SENTINEL": {
      "fw": "./shared/log-settings/syslog/entry[@name='AZURE_SENTINEL']",
      "pan": "./config/shared/log-settings/syslog/entry[@name='AZURE_SENTINEL']"
  }
}

fw_xpath = dict_xpath[config_key]["fw"]
pan_xpath = dict_xpath[config_key]["pan"]

# collect the data for firewalls, which common template they use.
# We dont know which is a common template, so we collect all templates.
file_show_ts = 'C:/Users/503395138.HCAD/Downloads/Panorama_new_20241004/show_template-stack.xml'
ts_tree = ET.parse(file_show_ts)
ts_root = ts_tree.getroot()
fw_data = {}
ts_data = {}
for ts in ts_root.findall("./result/template-stack/entry"):
    ts_name = getname(ts)
    ts_data[ts_name] = []
    tp_list = []
    for tp in ts.findall("./templates/member"):
        tp_list.append(tp.text)
        ts_data[ts_name].append(tp.text)

    for firewall in ts.findall("./devices/entry"):
        serial_number = firewall.find("./serial").text
        fw_name = firewall.find("./hostname").text
        fw_data[fw_name] = {}
        fw_data[fw_name]["serial"] = serial_number
        fw_data[fw_name]["templates"] = tp_list

files = get_xml_files(file_path)
output_dict = {"panorama-template": {}, "firewall": {}}
output_header_list = []

for xml_input in files:
    if os.path.getsize(xml_input) > 0:
        tree = ET.parse(xml_input)
        root = tree.getroot()
        if root.find("./panorama") is not None:
            print('its a panorama config.....................................')
            config_type = "panorama-template"
            for tmpl in root.findall("./devices/entry/template/entry"):
                tmpl_name = tmpl.attrib["name"]
                if tmpl_name not in output_dict[config_type]:
                    output_dict[config_type][tmpl_name] = {}
                # get the templates from the same stack of the current template
                for ts_name in ts_data:
                    if tmpl_name in ts_data[ts_name]:
                        output_dict[config_type][tmpl_name]["templates"] = "+".join(ts_data[ts_name])
                if "templates" not in output_dict[config_type][tmpl_name]:
                    output_dict[config_type][tmpl_name]["templates"] = "not_set"

                element = tmpl.findall(pan_xpath)
                subelements_dict = xml_to_line(element)
                for key, value in subelements_dict.items():
                    if key not in output_header_list:
                        output_header_list.append(key)
                    if value:
                        output_dict[config_type][tmpl_name][key] = '"' + value + '"'
                    else:
                        output_dict[config_type][tmpl_name][key] = "not_set"

        else:
            print('its a firewall config')
            config_type = "firewall"
            hostname = root.find("./devices/entry/deviceconfig/system/hostname").text
            if hostname not in output_dict[config_type]:
                output_dict[config_type][hostname] = {}
            element = root.findall(fw_xpath)
            subelements_dict = xml_to_line(element)
            for key, value in subelements_dict.items():
                if key not in output_header_list:
                    output_header_list.append(key)
                if value:
                    output_dict[config_type][hostname][key] = '"' + value + '"'
                else:
                    output_dict[config_type][hostname][key] = "not_set"

            if hostname in fw_data:
                output_dict[config_type][hostname]["templates"] = "+".join(fw_data[hostname]["templates"])
            else:
                output_dict[config_type][hostname]["templates"] = "not_set"

# check all element on all firewalls and set the value to not_set if element was not found
if len(output_dict["firewall"]) > 0:
    for config_item in output_header_list:
        for fw in output_dict["firewall"]:
            if output_dict["firewall"][fw].get(config_item) is None:
                output_dict["firewall"][fw][config_item] = "not_set"

# check all element on all firewalls and set the value to not_set if element was not found
if len(output_dict["panorama-template"]) > 0:
    for config_item in output_header_list:
        for tmpl in output_dict["panorama-template"]:
            if output_dict["panorama-template"][tmpl].get(config_item) is None:
                output_dict["panorama-template"][tmpl][config_item] = "not_set"

result = ''

first_tmpl = list(output_dict["panorama-template"].keys())[0]
header_list = ['type', 'template_or_hostname']
for element in sorted(output_dict["panorama-template"][first_tmpl]):
    header_list.append(element)
result += ','.join(header_list) + '\n'

for config_type in output_dict:
    for name in output_dict[config_type]:
        mylist = [config_type, name]
        for element in sorted(output_dict[config_type][name]):
            mylist.append(str(output_dict[config_type][name][element]))
        result += ','.join(mylist) + '\n'

    with open(result_output, 'w') as fp:
        fp.write(result)