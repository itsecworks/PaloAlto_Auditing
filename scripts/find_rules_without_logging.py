#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script finds rules with logging types.
#
import xml.etree.ElementTree as ET
import time

file_path = 'C:/Users/akdaniel/Downloads/'
xml_input = file_path + 'running-config.xml'
xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'paloalto_logging_audit_' + time_str + '.csv'

tree = ET.parse(xml_input)
root = tree.getroot()
pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
result_csv = "type, device-group, subtype, rulename\n"

for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        result = {}
        for rule_pos in ["pre-rulebase", "post-rulebase"]:
            rulebase = dg.find("./" + rule_pos)
            if rulebase is not None:
                if rulebase.findall("./security/rules/entry") is not None:
                    for rule in rulebase.findall("./security/rules/entry"):
                        rule_name = rule.attrib["name"]
                        if rule.find("./log-start") is not None and rule.find("./log-start").text == "yes":
                            result_csv += "{c0}, {c1}, {c2}, {c3}\n".format(c0="matched_on", c1=dg_name, c2="log_start", c3=rule_name)
                            if "log_start" not in result:
                                result["log_start"] = 1

                            else:
                                result["log_start"] += 1
                        if rule.find("./log-end") is not None and rule.find("./log-end").text == "no":
                            result_csv += "{c0}, {c1}, {c2}, {c3}\n".format(c0="matched_on", c1=dg_name, c2="no_log_end", c3=rule_name)
                            if "no_log_end" not in result:
                                result["no_log_end"] = 1
                            else:
                                result["no_log_end"] += 1
                        if rule.find("./log-setting") is not None:
                            lfp_name = rule.find("./log-setting").text
                            if lfp_name not in result:
                                result[lfp_name] = 1
                            else:
                                result[lfp_name] += 1
                        else:
                            result_csv += "{c0}, {c1}, {c2}, {c3}\n".format(c0="matched_on", c1=dg_name,
                                                                            c2="no_log_fwd", c3=rule_name)
                            if "no_log_fwd" not in result:
                                result["no_log_fwd"] = 1
                            else:
                                result["no_log_fwd"] += 1
        for data_type in result:
            result_csv += "{c0}, {c1}, {c2}, {c3}\n".format(c0="sum", c1=dg_name, c2=data_type, c3=result[data_type])

with open(result_output, 'w') as fp:
    fp.write(result_csv)