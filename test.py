
import json
import requests

headers = {
    'Content-Type': 'undefined',
  	'QB-Realm-Hostname': 'harriscounty.quickbase.com',
	'User-Agent': 'test',
	'Authorization': 'QB-USER-TOKEN b8qg7a_m8mu_0_hegv2qcy8r5bhbs8xvjdb7vhdaz'
}
body = {"to":"bum7eger8","data":[{"6":{"value":"202441742"},"7":{"value":"2024-11-14T17:20:18"},"9":{"value":"2024-11-14T17:20:26"},"12":{"value":"ARS - HCFMO ARSON INCIDENT"},"20":{"value":"BENTLEY ST"},"21":{"value":"-95.335451913831"},"22":{"value":"29.880536088631"},"23":{"value":"HOUSTON"},"25":{"value":"WESTFLD"},"26":{"value":"HCSO"}}],"fieldsToReturn":[6,7,8,9,12,13,20,21,22,23,24,25,26]}
r = requests.post(
'https://api.quickbase.com/v1/records', 
headers = headers, 
data = body
)

print(r.text)
