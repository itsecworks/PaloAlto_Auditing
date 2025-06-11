from bs4 import BeautifulSoup
import csv
import requests

url = "https://applipedia.paloaltonetworks.com/Home/GetApplicationListView"

# The data being posted (as raw form data)
payload = {
    "category": "",
    "subcategory": "",
    "technology": "",
    "risk": "",
    "characteristic": "",
    "searchstring": ""
}

# Send POST request
response = requests.post(url, data=payload)

# Save the response content to an HTML file
with open("C:/Users/danie/palo_alto_apps_html_table.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print("HTML table saved to palo_alto_apps_html_table.html")

soup = BeautifulSoup(response.text, "html.parser")

# Find the target html tbody
table_body = soup.find("tbody", id="bodyScrollingTable")
rows = table_body.find_all("tr")

# Prepare the CSV data
csv_data = []
headers = ["Name", "Category", "Subcategory", "Risk", "Technology"]
csv_data.append(headers)

for row in rows:
    cols = row.find_all("td")
    if not cols or len(cols) < 5:
        continue

    name = cols[0].get_text(strip=True)
    category = cols[1].get_text(strip=True)
    subcategory = cols[2].get_text(strip=True)

    # Risk level is in the image's title attribute
    risk_img = cols[3].find("img")
    risk = risk_img['title'].strip() if risk_img else ""

    technology = cols[4].get_text(strip=True)

    csv_data.append([name, category, subcategory, risk, technology])

# Write to CSV
with open("C:/Users/danie/palo_alto_applications.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(csv_data)

print("Data extracted and saved to palo_alto_applications.csv")
