#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Ist wurst...
#
# Description:
# -------------
# This script find the security rules and the security profile settings within panorama device-group hierarchy and give a report on their usage like no SPG or what kind of SPG and just SP with its members.
#
import xml.etree.ElementTree as ET
from typing import Any, List, Set, Dict
from xml.etree.ElementTree import Element, ElementTree
import time

# Function to find all anchestors for a device-group recursively
def find_ancestors(ro_element, child_dg):
        
    dg = ro_element.find("./devices/entry/device-group/entry[@name='" + child_dg + "']")
    if dg.find('./parent-dg') is not None and len(dg.find('./parent-dg').text) > 0:
            parent_dg = dg.find('./parent-dg').text
            # Recursively collect ancestors from the parent
            ancestors = find_ancestors(ro_element, parent_dg)
            # Add the current parent to the list of ancestors
            ancestors.append(parent_dg)
            return ancestors
    
    # Base case: If there is no parent (None or no text in tag parent-dg), return 'shared'    
    else:
        return ['shared']


def getname(element: Element) -> str:
    """

    :param element: the xml element from panorama xml configuration
    :return: it returns the name of the element. In panorama configuration it is the name attribute or the text of the xml element
    """
    if element.attrib is not None and 'name' in element.attrib:
        element_name: str = element.attrib["name"]
    else:
        element_name = element.text
    return element_name


def get_profile_names(profile_data: Element) -> str:
    """

    :param profile_data: the name of the profile set or the security profile group.
    :return: it shows the profile names used in security profile groups or used in security profiles
    """
    profile_list: list[str] = []
    element: str
    profiles_lst: list[str] = ["virus", "spyware", "vulnerability", "url-filtering", "file-blocking", "wildfire-analysis"]
    if len(profile_data) == 0:
        profile_list_str = "empty..."
    else:
        for element in profiles_lst:
            profile_type = element[0:3]
            element_xpath = "./" + element
            if profile_data.find(element_xpath) is not None:
                element_member_xpath = element_xpath + "/member"
                profile_value: str | None = profile_data.find(element_member_xpath).text
            else:
                profile_value = "NONE"
            profile_str: str = profile_type + "_" + profile_value
            profile_list.append(profile_str)
        profile_list_str: str = "+".join(profile_list)
    return profile_list_str


def get_parent_device_group(devg_name: str) -> str:
    """

    :param devg_name: it the device-group name  that we are looking a parent device-group name
    :return: "It returns the name of the parent device group"
    """
    readonly_dg: Element | None = ro_element.find("./devices/entry/device-group/entry[@name='" + devg_name + "']")
    if readonly_dg.find("./parent-dg") is not None:
        parent_dg_name: str | None = readonly_dg.find("./parent-dg").text
        return parent_dg_name
    else:
        return "shared"


def get_element_by_name(name: str, devg_name: str, obj_xpath: str) -> Element:
    """

    :param name: the name of the Element
    :param devg_name: the name of the device-group to use it in xpath for finding the element
    :param obj_xpath: the base xpath for the element list
    :return: It returns the xml Element with the name and with the xpath that is a parameter.
    """
    obj_found = ''
    if devg_name == "shared":
        dg_xpath: str = "./shared"
    else:
        dg_xpath = "./devices/entry/device-group/entry[@name='" + devg_name + "']"
    obj_xpath_full: str = dg_xpath + obj_xpath
    obj: Element
    for obj in root.findall(obj_xpath_full):
        obj_name: str = getname(obj)
        if obj_name == name:
            obj_found = obj
    if obj_found == '' and devg_name != "shared":
        dg_name_pr = get_parent_device_group(devg_name)
        return get_element_by_name(name, dg_name_pr, obj_xpath)
    else:
        return obj_found


def get_spyware_profile_action(profile_data: Element, devg_name: str, severity: str = "medium") -> str:
    """

    :param profile_data: profile sets or security profile group xml element from the security rule
    :param devg_name: the name of the device-group
    :param severity: the severity level
    :return: It returns the medium level action value from an anti-spyware security profile
    """
    spyware_mdm_action = "initial_value"
    sp_spyware_xpath: str = "/profiles/spyware/entry"

    sps_spyware_element = profile_data.find("./spyware/member")
    if sps_spyware_element is None:
        spyware_mdm_action = "no_spyware_used"
    else:
        spg_spyware_name = getname(sps_spyware_element)
        if spg_spyware_name == "default":
            spyware_mdm_action = "default-bi"
        elif spg_spyware_name == "strict":
            spyware_mdm_action = "reset-both-bi"
        else:
            spyware_xml = get_element_by_name(spg_spyware_name, devg_name, sp_spyware_xpath)
            for entry in spyware_xml.findall("./rules/entry"):
                entry_sev = entry.find("./severity")
                if severity in ET.tostring(entry_sev).decode():
                    spyware_mdm_action = entry.find("./action/").tag

    return spyware_mdm_action


def get_custom_url_cat_action(profile_data: Element, devg_name: str) -> dict:
    """

    :param profile_data: profile sets or security profile group xml element from the security rule
    :param devg_name: the name of the device-group
    :return:
    """
    url_categories: set[str] = {"abortion", "abused-drugs", "adult", "alcohol-and-tobacco", "artificial-intelligence",
                                "auctions", 'business-and-economy', "command-and-control", "computer-and-internet-info",
                                "content-delivery-networks", "copyright-infringement", "cryptocurrency", "dating",
                                "dynamic-dns", "educational-institutions", "encrypted-dns", "entertainment-and-arts",
                                "extremism", "financial-services", "gambling", "games", "government", "grayware",
                                "hacking", "health-and-medicine", "high-risk", "home-and-garden", "hunting-and-fishing",
                                "insufficient-content", "internet-communications-and-telephony", "internet-portals",
                                "job-search", "legal", "low-risk", "malware", "medium-risk", "military",
                                "motor-vehicles", "music", "newly-registered-domain", "news", "not-resolved", "nudity",
                                "parked", "peer-to-peer", "personal-sites-and-blogs",
                                "philosophy-and-political-advocacy",
                                "phishing", "private-ip-addresses", "proxy-avoidance-and-anonymizers", "questionable",
                                "ransomware", "real-estate", "real-time-detection", "recreation-and-hobbies",
                                "reference-and-research", "religion", "scanning-activity", "search-engines",
                                "sex-education", "shareware-and-freeware", "shopping", "social-networking", "society",
                                "sports", "stock-advice-and-tools", "streaming-media", "swimsuits-and-intimate-apparel",
                                "training-and-tools", "translation", "travel", "unknown", "weapons",
                                "web-advertisements", "web-based-email", "web-hosting", "online-storage-and-backup"}

    sp_url_filter_xpath: str = "/profiles/url-filtering/entry"
    action_list: list[str] = ["allow", "alert", "block"]
    cust_url_categories: dict[str, list[Any]] = {}

    sps_url_filter_xml: Element | None = profile_data.find("./url-filtering/member")
    if sps_url_filter_xml is None:
        for action in action_list:
            cust_url_categories[action] = ["no_url_filter_profile"]
    else:
        sps_url_filter_name = getname(sps_url_filter_xml)
        sp_url_filter_xml: Element = get_element_by_name(sps_url_filter_name, devg_name, sp_url_filter_xpath)
        if "ransomware" not in ET.tostring(sp_url_filter_xml).decode():
            print("ransomware action not set on: ", sps_url_filter_name, " device-group: ", devg_name)
        for action in action_list:
            cust_url_categories[action] = []
            action_xpath = "./" + action + "/member"
            for member in sp_url_filter_xml.findall(action_xpath):
                if member.text not in url_categories:
                    # we found a custom url category
                    cust_url_categories[action].append(member.text)
            if len(cust_url_categories[action]) == 0:
                cust_url_categories[action] = ["no_custom_url_category_in_action"]
    return cust_url_categories


def security_profile_audit_by_rules(devg_name: str, devg_rulebase: Element) -> str:
    """

    :param devg_name: the name of the device-group
    :param devg_rulebase:  this is an element from the configuration that contains the rules
    :return: it returns a big csv with details on security profile settings
    """
    csv_lines: str = ''
    c = 0
    dict_pgs: dict[Any, Any] = {devg_name: {}}
    spg_xpath: str = "/profile-group/entry"

    sec_rules_xml: Element = devg_rulebase.find("./security/rules")
    rulebase_pos = devg_rulebase.tag

    if devg_name == "shared":
        dg_ancestors = ["shared"]
    else:
        dg_ancestors = find_ancestors(ro_element, devg_name)
    dg_anc_str: str = "+".join(dg_ancestors)

    if sec_rules_xml is not None:
        for rule_xml in sec_rules_xml:
            # profile-setting exists
            cust_url_cat_action_dict = {}
            spyware_mdm_action = ""
            if rule_xml.find("./profile-setting") and rule_xml.find("./action").text == "allow":
                # group used in profile setting
                if rule_xml.find("./profile-setting/group"):
                    rule_name = rule_xml.attrib["name"]
                    action = rule_xml.find("./action").text
                    if str(rule_xml.find("./to/member").text).lower() == "trust" and str(rule_xml.find("./from/member").text).lower() == "trust":
                        print(rule_name, "is trust to trust")
                    if rule_xml.find("./disabled") is not None:
                        disabled_state = rule_xml.find("./disabled").text
                    else:
                        disabled_state = "no"
                    rule_spg_name = rule_xml.find("./profile-setting/group/member").text
                    # find the spg through the dg hierarchy
                    spg_xml = get_element_by_name(rule_spg_name, devg_name, spg_xpath)
                    profiles_str = get_profile_names(spg_xml)
                    # get medium level spyware by function
                    spyware_mdm_action = get_spyware_profile_action(spg_xml, devg_name)
                    # get custom url category actions by function
                    cust_url_cat_action_dict = get_custom_url_cat_action(spg_xml, dg_name)
                    cust_url_cat_action_block_str = "+".join(cust_url_cat_action_dict["block"])
                    cust_url_cat_action_alert_str = "+".join(cust_url_cat_action_dict["alert"])
                    cust_url_cat_action_allow_str = "+".join(cust_url_cat_action_dict["allow"])

                    if rule_spg_name not in dict_pgs[devg_name]:
                        dict_pgs[devg_name][rule_spg_name] = {}
                        dict_pgs[devg_name][rule_spg_name]["count"] = 1
                        dict_pgs[devg_name][rule_spg_name]["set"] = profiles_str
                    else:
                        dict_pgs[devg_name][rule_spg_name]["count"] += 1
                    csv_lines += "{c0}, {c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}, {c9}, {c10}, {c11}\n".format(c0=dg_anc_str,
                                                                                                 c1=devg_name,
                                                                                                 c2=rulebase_pos,
                                                                                                 c3=rule_name,
                                                                                                 c4=action,
                                                                                                 c5=rule_spg_name,
                                                                                                 c6=profiles_str,
                                                                                                 c7=disabled_state,
                                                                                                 c8=spyware_mdm_action,
                                                                                                 c9=cust_url_cat_action_block_str,
                                                                                                 c10=cust_url_cat_action_alert_str,
                                                                                                 c11=cust_url_cat_action_allow_str)
                # empty group or profiles used in profile setting
                elif (rule_xml.find("./profile-setting/group") is not None and len(rule_xml.find("./profile-setting/group")) == 0) or (rule_xml.find("./profile-setting/profiles") is not None and len(rule_xml.find("./profile-setting/profiles")) == 0):
                    rule_name = rule_xml.attrib["name"]
                    action = rule_xml.find("./action").text
                    if rule_xml.find("./disabled") is not None:
                        disabled_state = rule_xml.find("./disabled").text
                    else:
                        disabled_state = "no"
                    csv_lines += "{c0}, {c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}, {c9}, {c10}, {c11}\n".format(c0=dg_anc_str,
                                                                                                 c1=devg_name,
                                                                                                 c2=rulebase_pos,
                                                                                                 c3=rule_name,
                                                                                                 c4=action,
                                                                                                 c5="no-profile-group2",
                                                                                                 c6="no-profile-setting2",
                                                                                                 c7=disabled_state,
                                                                                                 c8="NA",
                                                                                                 c9="NA",
                                                                                                 c10="NA",
                                                                                                 c11="NA")
                    c += 1

                # profiles used in profile setting
                else:
                    rule_name = rule_xml.attrib["name"]
                    action = rule_xml.find("./action").text
                    if rule_xml.find("./disabled") is not None:
                        disabled_state = rule_xml.find("./disabled").text
                    else:
                        disabled_state = "no"

                    profiles_xml = rule_xml.find("./profile-setting/profiles")
                    # profile sets in a rule have the same structure as a profile-group object
                    # get_profiles_str can be reused.
                    profiles_str = get_profile_names(profiles_xml)
                    # get medium level spyware by function
                    spyware_mdm_action = get_spyware_profile_action(profiles_xml, devg_name)
                    # get custom url category actions by function
                    cust_url_cat_action_dict = get_custom_url_cat_action(profiles_xml, dg_name)
                    cust_url_cat_action_block_str = "+".join(cust_url_cat_action_dict["block"])
                    cust_url_cat_action_alert_str = "+".join(cust_url_cat_action_dict["alert"])
                    cust_url_cat_action_allow_str = "+".join(cust_url_cat_action_dict["allow"])

                    if profiles_str not in dict_pgs[devg_name]:
                        dict_pgs[devg_name][profiles_str] = {}
                        dict_pgs[devg_name][profiles_str]["count"] = 1
                        dict_pgs[devg_name][profiles_str]["set"] = profiles_str
                    else:
                        dict_pgs[devg_name][profiles_str]["count"] += 1
                    csv_lines += "{c0}, {c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}, {c9}, {c10}, {c11}\n".format(c0=dg_anc_str,
                                                                                                 c1=devg_name,
                                                                                                 c2=rulebase_pos,
                                                                                                 c3=rule_name,
                                                                                                 c4=action,
                                                                                                 c5="no-profile-group",
                                                                                                 c6=profiles_str,
                                                                                                 c7=disabled_state,
                                                                                                 c8=spyware_mdm_action,
                                                                                                 c9=cust_url_cat_action_block_str,
                                                                                                 c10=cust_url_cat_action_alert_str,
                                                                                                 c11=cust_url_cat_action_allow_str)

            # no profile-setting at all
            elif rule_xml.find("./profile-setting") is None and rule_xml.find("./action").text == "allow":
                rule_name = rule_xml.attrib["name"]
                action = rule_xml.find("./action").text
                if rule_xml.find("./disabled") is not None:
                    disabled_state = rule_xml.find("./disabled").text
                else:
                    disabled_state = "no"
                csv_lines += "{c0}, {c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}, {c9}, {c10}, {c11}\n".format(c0=dg_anc_str,
                                                                                             c1=devg_name,
                                                                                             c2=rulebase_pos,
                                                                                             c3=rule_name, c4=action,
                                                                                             c5="no-profile-group",
                                                                                             c6="no-profile-setting",
                                                                                             c7=disabled_state,
                                                                                             c8="NA",
                                                                                             c9="NA",
                                                                                             c10="NA",
                                                                                             c11="NA")
                c += 1

        # counter for rules without profile-setting
        csv_lines += "{c0}, {c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}, {c9}, {c10}, {c11}, {c12}\n".format(c0=dg_anc_str,
                                                                                           c1=devg_name,
                                                                                           c2=rulebase_pos,
                                                                                           c3="NA", c4="NA",
                                                                                           c5="no-profile-group",
                                                                                           c6="no-profile-setting",
                                                                                           c7="NA", c8="NA",
                                                                                           c9="NA", c10="NA", c11="NA",
                                                                                           c12=str(c))

        # counter for groups in profile-setting
        for spg_name in dict_pgs[devg_name]:
            csv_lines += "{c0}, {c1}, {c2}, {c3}, {c4}, {c5}, {c6}, {c7}, {c8}, {c9}, {c10}, {c11}, {c12}\n".format(c0=dg_anc_str,
                                                                                               c1=devg_name,
                                                                                               c2=rulebase_pos,
                                                                                               c3="NA", c4="NA",
                                                                                               c5=spg_name,
                                                                                               c6=str(dict_pgs[devg_name][spg_name]["set"]),
                                                                                               c7="NA",
                                                                                               c8="NA",
                                                                                               c9="NA",
                                                                                               c10="NA",
                                                                                               c11="NA",
                                                                                               c12=str(dict_pgs[devg_name][spg_name]["count"]))

    return csv_lines


file_path = 'C:/Users/akdaniel/Downloads/running-config/'
xml_input = file_path + 'running-config.xml'
# xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
print("start: ", time_str)
result_output = file_path + 'sec_profile_audit_' + time_str + '.csv'

tree: ElementTree = ET.parse(xml_input)
root: Element | Any = tree.getroot()
ro_element: Element | None = root.find("./readonly")

result: str = ("dg_parents, dg_name, rule_position, rule_name, action, profile-group, profile-settings, "
               "disabled_state, spyware-medium-action, custom_url_blocks, custom_url_alerts, custom_url_allows, sum\n")
rule_pos_list: list[str] = ["pre", "post"]
pa_all_dgs: dict[str, str] = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
key: str
for key in pa_all_dgs:
    xpath: str = pa_all_dgs[key]
    dg: Element
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        for rule_pos in rule_pos_list:
            xpath_rulebase = "./" + rule_pos + "-rulebase"
            dg_rulebase = dg.find(xpath_rulebase)
            if dg_rulebase is not None:
                result += security_profile_audit_by_rules(dg_name, dg_rulebase)

with open(result_output, 'w') as fp:
    fp.write(result)

time_str = time.strftime("%Y%m%d_%H%M%S")
print("finish: ", time_str)
