import xml.etree.ElementTree as ET
import json
import pdb

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
        if dg.find('./parent-dg') is not None and len(dg.find('./parent-dg').text) > 0:
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


# Function to build the device-group tree recursively
def build_tree(dg_children, parent):

    children = dg_children.get(parent, [])
    tree = {}
    for child in children:
        tree[child] = build_tree(dg_children, child)
    return tree

dg_children = find_children(ro_element)

# Build the hierarchical tree starting from the root
dg_hierarhcy = build_tree(dg_children, 'shared')

# Convert the family tree to JSON
dg_hierarhcy_json = json.dumps(dg_hierarhcy, indent=2)

# Print the family tree in JSON format
print(dg_hierarhcy_json)

# Print descendants for the given device-group
dg_list = find_descendants(dg_children, "america")
print(dg_list)

# Print anchestors for the given device-group
dg_list = find_ancestors(ro_element, "paris")
print(dg_list)

# Iterate over all device-group in the xml including shared
pa_all_dgs = {"shared": "./shared", "default": "./devices/entry/device-group/entry"}
for key in pa_all_dgs:
    xpath = pa_all_dgs[key]
    for dg in root.findall(xpath):
        if key == "default":
            dg_name = dg.attrib["name"]
        else:
            dg_name = key
        print(dg_name)
