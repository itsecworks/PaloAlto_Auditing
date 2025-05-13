import xml.etree.ElementTree as ET
import json

# Path to the Panorama XML configuration file
xml_file = 'C:/temp/csaba/config.xml'

# Parse the XML data
tree = ET.parse(xml_file)
root = tree.getroot()
ro_element = root.find("./readonly")

# Function to find all children to each device-group
def find_children(ro_element):

    # we create a dictionary with key as the device-group and with value as a list of direct child device-groups
    dg_children = {}
    dg_children['shared'] = []
    for dg in ro_element.findall('./devices/entry/device-group/entry'):
        dg_name = dg.get('name')
        dg_parent = dg.find('./parent-dg')
        if dg_parent is not None and len(dg_parent.text) > 0:
            parent_dg_name = dg.find('./parent-dg').text
        else:
            parent_dg_name = 'shared'
            
        if parent_dg_name not in dg_children:
            dg_children[parent_dg_name] = [dg_name]
        else:
            dg_children[parent_dg_name].append(dg_name)

    return (dg_children)

# Function to find all descendants fora a device-group recursively
def find_descendants(dg_children, parent_dg):
    
    dg_descendants = []  # List to store descendants of a device-group
    # Find all children of the given parent
    if parent_dg in dg_children:
        children = dg_children[parent_dg]
    
        for child in children:
            # add a single list element to the descendant list
            dg_descendants.append(child)
            # extend with multiple list elements the device-group with recursively get descendants
            dg_descendants.extend(find_descendants(dg_children, child)) 
    
    return dg_descendants

# Function to find all ancestors for a device-group recursively
def find_ancestors(ro_element, child_dg):

    if "shared" in child_dg:
        return []

    dg = ro_element.find("./devices/entry/device-group/entry[@name='" + child_dg + "']")
    dg_parent = dg.find('./parent-dg')
    if dg_parent is not None and len(dg_parent.text) > 0:
        parent_dg = dg.find('./parent-dg').text
        # Recursively collect ancestors from the parent
        ancestors = find_ancestors(ro_element, parent_dg)
        # Add the current parent to the list of ancestors
        ancestors.append(parent_dg)
        return ancestors

    # Base case: If there is no parent (None or no text in tag parent-dg), return 'shared'
    else:
        return ['shared']


# Function to build the device-group tree recursively
def build_tree(dg_children, parent):

    children = dg_children.get(parent, [])
    tree = {}
    for child in children:
        tree[child] = build_tree(dg_children, child)
    return tree

dg_children = find_children(ro_element)

# Build the hierarchical tree starting from the root
dg_name = 'shared'
dg_hierarhcy = build_tree(dg_children, dg_name)
# Convert the family tree to JSON
dg_hierarhcy_json = json.dumps(dg_hierarhcy, indent=2)
# Print the family tree in JSON format
print(f'tree view for the device-group {dg_name}:')
print(dg_hierarhcy_json)

# Print descendants for the given device-group
dg_name = 'america'
dg_list = find_descendants(dg_children, dg_name)
print(f'descendants for the device-group {dg_name} : {dg_list}')

# Print ancestors for the given device-group
dg_name = 'paris'
dg_list = find_ancestors(ro_element, dg_name)
print(f'ancestors of {dg_name} device-group:  {dg_list}')

# Iterate over the device-group policies from paris perspective
rule_pos_list: list[str] = ["pre", "post"]
print(f'the right order to check rulebase objects for the device-group {dg_name}:')
dg_list.append(dg_name)
for rule_pos in rule_pos_list:
    print(f'rule position {rule_pos}:')
    xpath_rulebase = "./" + rule_pos + "-rulebase"
    for dg in reversed(dg_list):
        print(f'device-group {dg}, with rulebase {rule_pos}-rulebase')

# Iterate over all device-group pre and post rulebase in the xml including shared generally
print('all device-groups configured:')
rule_pos_list: list[str] = ["pre", "post"]
pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        for rule_pos in rule_pos_list:
            xpath_rulebase = "./" + rule_pos + "-rulebase"
            dg_rulebase = dg.find(xpath_rulebase)
            print(f'device-group {dg_name}, with rulebase {rule_pos}-rulebase')
