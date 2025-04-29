import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict

# XML input (you would normally load this from a file or API)
xml_data = """
<response status="success">
    <result>
        <rule-hit-count>
            <device-group>
                <entry name="dg_ny-dc">
                    <rule-base>
                        <entry name="security">
                            <rules>
                                <entry name="ntp-google-allow">
                                    <rule-state>Used</rule-state>
                                    <all-connected>yes</all-connected>
                                    <rule-creation-timestamp>1709039742</rule-creation-timestamp>
                                    <rule-modification-timestamp>1745422778</rule-modification-timestamp>
                                </entry>
                                <entry name="dns-google-allow">
                                    <rule-state>Used</rule-state>
                                    <all-connected>yes</all-connected>
                                    <rule-creation-timestamp>1731122778</rule-creation-timestamp>
                                    <rule-modification-timestamp>1731122778</rule-modification-timestamp>
                                </entry>
                                <entry name="sdns-google-allow">
                                    <rule-state>Used</rule-state>
                                    <all-connected>yes</all-connected>
                                    <rule-creation-timestamp>1732122211</rule-creation-timestamp>
                                    <rule-modification-timestamp>1732122211</rule-modification-timestamp>
                                </entry>                                
                                <entry name="pan-mgmt-allow">
                                    <rule-state>Used</rule-state>
                                    <all-connected>yes</all-connected>
                                    <rule-creation-timestamp>1709039742</rule-creation-timestamp>
                                    <rule-modification-timestamp>1709039742</rule-modification-timestamp>
                                </entry>
                            </rules>
                        </entry>
                    </rule-base>
                </entry>
            </device-group>
        </rule-hit-count>
    </result>
</response>
"""

def find_unused_rules(rules, months_threshold=2):
    threshold_date = datetime.now() - timedelta(days=months_threshold * 30)
    now = datetime.now()
    old_unused_rules = defaultdict(list)

    for rule in rules:
        rule_name = rule.attrib.get('name')
        rule_state = rule.findtext('rule-state')
        mod_timestamp = rule.findtext('rule-modification-timestamp')

        if not mod_timestamp:
            continue

        mod_datetime = datetime.fromtimestamp(int(mod_timestamp))
        age_days = (now - mod_datetime).days
        age_month = age_days // 30

        if rule_state == 'Used' and mod_datetime < threshold_date:
            old_unused_rules[age_month].append({
                'rule_name': rule_name,
                'last_modified': mod_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'age_days': age_days
            })

    return old_unused_rules

# Parse XML
root = ET.fromstring(xml_data)
rules = root.findall('.//rules/entry')

# Find and print old unused rules
grouped_rules = find_unused_rules(rules)
print("Rules not used for more than 2 months (grouped by age in months):")
for age_month in sorted(grouped_rules.keys(), reverse=True):
    print(f"\nAge: {age_month} month(s)")
    for rule in grouped_rules[age_month]:
        print(f"- {rule['rule_name']} | Last Modified: {rule['last_modified']} | Age: {rule['age_days']} days")
