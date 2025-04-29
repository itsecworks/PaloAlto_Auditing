import xml.etree.ElementTree as ET
from collections import defaultdict

# the best approach is the hitcounts from dataplane with api call on firewalls:
# type=op&cmd=<show><rule-hit-count><vsys><vsys-name><entry name='vsys1'><rule-base><entry name='security'><rules><all/></rules></entry></rule-base></entry></vsys-name></vsys></rule-hit-count></show>

# Sample XML data
xml_data_fw = """
<response status="success">
    <result>
        <rule-hit-count>
            <vsys>
                <entry name="vsys1">
                    <rule-base>
                        <entry name="security">
                            <rules>
                                <entry name="ntp-google-allow">
                                    <latest>yes</latest>
                                    <hit-count>247565223</hit-count>
                                    <last-hit-timestamp>1745707970</last-hit-timestamp>
                                    <last-reset-timestamp>0</last-reset-timestamp>
                                    <first-hit-timestamp>1709041868</first-hit-timestamp>
                                    <rule-creation-timestamp>1709041868</rule-creation-timestamp>
                                    <rule-modification-timestamp>1745596208</rule-modification-timestamp>
                                </entry>
                                <entry name="pan-mgmt-allow">
                                    <latest>yes</latest>
                                    <hit-count>2425</hit-count>
                                    <last-hit-timestamp>1741884635</last-hit-timestamp>
                                    <last-reset-timestamp>0</last-reset-timestamp>
                                    <first-hit-timestamp>1738155537</first-hit-timestamp>
                                    <rule-creation-timestamp>1709041868</rule-creation-timestamp>
                                    <rule-modification-timestamp>1731380226</rule-modification-timestamp>
                                </entry>
                                <entry name="tor_deny">
                                    <latest>yes</latest>
                                    <hit-count>0</hit-count>
                                    <last-hit-timestamp>0</last-hit-timestamp>
                                    <last-reset-timestamp>0</last-reset-timestamp>
                                    <first-hit-timestamp>0</first-hit-timestamp>
                                    <rule-creation-timestamp>1718088048</rule-creation-timestamp>
                                    <rule-modification-timestamp>1732803542</rule-modification-timestamp>
                                </entry>
                            </rules>
                        </entry>
                    </rule-base>
                </entry>
            </vsys>
        </rule-hit-count>
    </result>
</response>
"""


def find_old_rules(xml_string, threshold_months=2, days_per_month=30):
    # Parse the XML
    root = ET.fromstring(xml_string)

    # Calculate threshold in seconds
    threshold_seconds = threshold_months * days_per_month * 24 * 60 * 60

    # Collect rules older than threshold
    old_rules = defaultdict(list)

    for rule in root.findall(".//rules/entry"):
        name = rule.attrib.get("name")
        last_hit = int(rule.findtext("last-hit-timestamp", default="0"))
        mod_time = int(rule.findtext("rule-modification-timestamp", default="0"))

        if last_hit == 0 or mod_time == 0:
            continue

        age_seconds = last_hit - mod_time
        if age_seconds > threshold_seconds:
            age_days = age_seconds // (24 * 60 * 60)
            age_months = age_days // days_per_month
            old_rules[age_months].append((name, age_days))

    return dict(sorted(old_rules.items()))


# Run the function and print results
if __name__ == "__main__":
    result = find_old_rules(xml_data_fw)
    for months, rules in result.items():
        print(f"\nRules older than {months} month(s):")
        for rule_name, age_in_days in rules:
            print(f" - {rule_name} (Age: {age_in_days} days)")
