import xml.etree.ElementTree as ET
import time

file_path = 'C:/Users/dakos/Downloads/'
xml_input = file_path + '6308.xml'
#xml_output = xml_input.replace('.xml','_mod.xml')
time_str = time.strftime("%Y%m%d_%H%M%S")
result_output = file_path + 'sec_rules_audit_' + time_str + '.csv'


def sec_rule_check(dg_name, entry):


    result = ''
    dict_bad_rules = {}
    sec_rules = entry.find("./security/rules")
    if sec_rules is not None:
        for rule in sec_rules:
            # src and src-user any
            if rule.find("./source/member").text == "any" and rule.find("./source-user") and rule.find("./action").text == "allow":
                if rule.find("./source-user/member").text == "any":
                    rule_name = rule.attrib["name"]
                    result += "src" + "," + dg_name + "," + rule_name + "\n"
                    if "src" not in dict_bad_rules:
                        dict_bad_rules["src"] = 1
                    else:
                        dict_bad_rules["src"] += 1

            # dst any
            if rule.find("./destination/member").text == "any" and rule.find("./category") and rule.find("./action").text == "allow":
                if rule.find("./category/member").text == "any":
                    rule_name = rule.attrib["name"]
                    result += "dst" + "," + dg_name + "," + rule_name + "\n"
                    if "dst" not in dict_bad_rules:
                        dict_bad_rules["dst"] = 1
                    else:
                        dict_bad_rules["dst"] += 1

            # svc any and app any
            if rule.find("./service/member").text == "any" and rule.find("./application/member").text == "any" and rule.find("./action").text == "allow":
                rule_name = rule.attrib["name"]
                result += "svc" + "," + dg_name + "," + rule_name + "\n"
                if "svc" not in dict_bad_rules:
                    dict_bad_rules["svc"] = 1
                else:
                    dict_bad_rules["svc"] += 1

            # to zone any
            if rule.find("./to/member").text == "any" and rule.find("./action").text == "allow":
                rule_name = rule.attrib["name"]
                result += "dst_zone" + "," + dg_name + "," + rule_name + "\n"
                if "dst_zone" not in dict_bad_rules:
                    dict_bad_rules["dst_zone"] = 1
                else:
                    dict_bad_rules["dst_zone"] += 1

            # from zone any
            if rule.find("./from/member").text == "any" and rule.find("./action").text == "allow":
                rule_name = rule.attrib["name"]
                result += "src_zone" + "," + dg_name + "," + rule_name + "\n"
                if "src_zone" not in dict_bad_rules:
                    dict_bad_rules["src_zone"] = 1
                else:
                    dict_bad_rules["src_zone"] += 1

    for key in dict_bad_rules:
        result += key + "_sum," + dg_name + "," + str(dict_bad_rules[key]) + "\n"
    return result


tree = ET.parse(xml_input)
root = tree.getroot()

result = ''
rule_pos_list = ["pre", "post"]
pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        for entry in rule_pos_list:
            xpath = "./" + entry + "-rulebase"
            dg_rulebase = dg.find(xpath)
            if dg_rulebase is not None:
                result += sec_rule_check(dg_name, dg_rulebase)

with open(result_output, 'w') as fp:
    fp.write(result)