import json
import requests
import time
import logging
from datetime import datetime

#configure logging
logging.basicConfig(filename='notify_two_units.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def is_night_time():
    current_hour = datetime.now().hour
    return current_hour >= 17 or current_hour < 6

def eastcommtoken():
    global eastcomm_cookie
    url = "http://webcad.ehcec.net/User/ExecuteSignIn"

    payload = json.dumps({
      "userName": "hcfmo",
      "password": "hcfmo",
      "remember": False
    })
    headers = {
      'authority': 'webcad.ehcec.net',
      'accept': 'application/json, text/plain, */*',
      'accept-language': 'en-US,en;q=0.9,es;q=0.8',
      'content-type': 'application/json',
      'origin': 'https://webcad.ehcec.net',
      'referer': 'https://webcad.ehcec.net/',
      'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'empty',
      'sec-fetch-mode': 'cors',
      'sec-fetch-site': 'same-origin',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    eastcomm_cookie = response.cookies.get_dict()['webCAD']
    eastcomm_cookie = 'webCAD=' + eastcomm_cookie
    logging.info(f'Updated cookie: {eastcomm_cookie}')
    return

def eastCommIncidentDetails(incidentID):
    """ This function pulls incident details from the ECOMM CAD. It requires an updated cookie from the WebCAD. """
    url = "http://webcad.ehcec.net/IncidentDetails/GetFireIncidentPreview?getNotes=false&incidentNumber=" + incidentID

    payload={}
    headers = {
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
      'Connection': 'keep-alive',
      'Cookie': eastcomm_cookie,
      'Referer': 'http://webcad.ehcec.net/index.html',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    resp = response.json()
    json_results = json.loads(resp)
    #rtn = json_results['Location']
    return json_results

def activeIncidentCount():

    url = "http://webcad.ehcec.net/Incidents/GetCounts"

    payload={}
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
        'Connection': 'keep-alive',
        'Cookie': eastcomm_cookie,
        'Referer': 'http://webcad.ehcec.net/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
        }
    
    response = requests.request("GET", url, headers=headers, data=payload)
    json_results = response.json()
    logging.info('Active incidents Pulled')
    return json_results

def getActiveIncidents():
    url = "http://webcad.ehcec.net/Incidents/GetFireActiveIncidents"

    payload={}
    headers = {
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
      'Connection': 'keep-alive',
      'Cookie': eastcomm_cookie,
      'Referer': 'http://webcad.ehcec.net/index.html',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    json_results = response.json()
    return json_results

def ntfy(message, priority):
  url = "http://defcon.singletonwiki.com/hcfmo"

  payload = message
  headers = {
    'Authorization': 'Bearer tk_mox1lne2ezy6nool3pk6ieefy9e43',
    'X-Priority': str(priority),
  }

  response = requests.request("POST", url, headers=headers, data=payload)
  return


try:
    ntfy('Starting to monitor webCAD', 1)
    # Set to store incident numbers we've already notified about
    notified_incidents = set()
    responding_incidents = set()
    # Set to store incident numbers we've sent unit notifications for
    unit_notified_incidents = set()
except Exception as e:
    logging.error('Failed to send notification')

try:
    eastcommtoken()
    logging.info('Starting to monitor webCAD')
except Exception as e:
    logging.error('Failed to get token')
    ntfy('Failed to get token', 3)


def main_loop():
    
    activecount = activeIncidentCount()
    if activecount['ActiveFire'] > 0:
        activeincidents = getActiveIncidents()
        logging.info(activeincidents)
        for incident in activeincidents:
            incident_num = incident["IncidentNumber"]
            logging.info(f'Checking Incident for Arson: {incident_num}')
            
            if incident['NatureCode'] == 'ARS' and incident_num not in notified_incidents:
                logging.info(f'Arson Incident Found: {incident["LocationAddress"]} near {incident["CrossStreet1"]}, {incident["FireJurisdictionDescription"]}. ')
                logging.debug(incident)
                ntfy(f'Arson Incident Found: {incident["LocationAddress"]} near {incident["CrossStreet1"]}, {incident["FireJurisdictionDescription"]}. LE is {incident["LawJurisdictionDescription"]}. {incident["UnitName2"]} picked up the call.', 2)
                notified_incidents.add(incident_num)

            if incident['NatureCode'] == 'ARS' and incident['ElapsedCall'] > "00:08:00" and incident_num not in responding_incidents:
                ntfy(f'Incident {incident_num} at {incident["LocationAddress"]} on {incident["CallDate"]} has exceeded 8 minutes. Units {incident["UnitName1"]}, {incident["UnitName2"]}, {incident["UnitName3"]}, {incident["UnitName4"]} are responding.', 5)
                responding_incidents.add(incident_num)
            
            if incident['NatureCode'] == 'ARS' and incident['UnitName3'] is not None and 'F' in incident['UnitName3'] and incident_num not in unit_notified_incidents:
                ntfy(incident['UnitName2'] + ' ' + incident['UnitName3'] + ' ' + incident['UnitName4'] + ' are responding to an arson incident at ' + incident['LocationAddress'] + ' app.responder360.com', 5)
                unit_notified_incidents.add(incident_num)
            else:
                if incident['NatureCode'] == 'ARS' and incident['UnitName3'] == 'INSP' or 'P' in incident['UnitName3']:
                    logging.info(f'{incident["UnitName3"]} is an inspector: {incident_num}')
        time.sleep(120)
    time.sleep(40)


while is_night_time():
    try:
        main_loop()
    except Exception as e:
        logging.error(f"Error occured: {e}")
        eastcommtoken()
        time.sleep(1)
else:
    logging.info('Daytime, exiting script.')
    ntfy('Ending script', 1)


