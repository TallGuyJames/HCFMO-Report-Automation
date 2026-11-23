import json
import requests
import time
import sqlite3
import logging
from datetime import datetime
import os

def setup():
    # Set up logging with absolute path and error handling
    try:
        log_path = os.path.abspath('incidents.log')
        logging.basicConfig(
            filename=log_path,
            filemode='a', 
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info(f'Log file initialized at: {log_path}')
    except Exception as e:
        print(f"Failed to set up logging: {str(e)}")
        raise  # Re-raise the exception to see the full error
    
    # Force flush the log buffer
    logging_handler = logging.getLogger().handlers[0]
    logging_handler.flush()
    
    logging.info('Initializing application')
    print('Initializing application')
    
    # Initialize QuickBase connection
    logging.debug('Connecting to QuickBase')
    
    # QuickBase API configuration
    global QB_REALM, QB_AUTH, QB_APP_ID, QB_TABLE_ID, QB_HEADERS
    QB_REALM = "harriscounty" # Your QuickBase realm
    QB_AUTH = "QB-USER-TOKEN b8qg7a_m8mu_0_hegv2qcy8r5bhbs8xvjdb7vhdaz"  # Your auth token
    QB_APP_ID = "br9m5jiev"  # Investigation app ID
    
    QB_HEADERS = {
        'QB-Realm-Hostname': QB_REALM,
        'Authorization': QB_AUTH,
        'Content-Type': 'application/json'
    }
    
    # Test connection with a simple query
    try:
        url = f'https://api.quickbase.com/v1//fields?tableId=bum7eger8&includeFieldPerms=false'
        response = requests.get(url, headers=QB_HEADERS)
        response.raise_for_status()
        logging.info('Successfully connected to QuickBase')
    except Exception as e:
        logging.error(f'Failed to connect to QuickBase: {str(e)}')
        raise
        
    # Initialize database
    logging.debug('Connecting to SQLite database')
    conn = sqlite3.connect('incidents.db')
    cursor = conn.cursor()
    
    logging.debug('Creating incidents table if it does not exist')
    cursor.execute('''CREATE TABLE IF NOT EXISTS incidents
                 (incident_number text, life_cycle integer, naturecode text,timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    logging.info('Database initialization complete')
    logging_handler.flush()

    return QB_HEADERS, conn, cursor

def eastcommtoken():
    logging.debug('Requesting new EastComm token')
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

    logging.debug('Sending token request')
    response = requests.request("POST", url, headers=headers, data=payload)
    eastcomm_cookie = response.cookies.get_dict()['webCAD']
    eastcomm_cookie = 'webCAD=' + eastcomm_cookie
    logging.info(f'Updated cookie: {eastcomm_cookie}')
    logging.getLogger().handlers[0].flush()
    print(f'Updated cookie: {eastcomm_cookie}')
    return

def get_closed_incidents_from_db():
    """Get all incidents with life cycle 5 from database"""
    conn = sqlite3.connect('incidents.db')
    cursor = conn.cursor()
    cursor.execute('SELECT incident_number FROM incidents WHERE life_cycle = 5')
    closed_incidents = cursor.fetchall()
    conn.close()
    return [incident[0] for incident in closed_incidents]

def getClosedIncident(incident_number):
    """Fetch incident details from EastComm CAD"""
    url = f"http://webcad.ehcec.net/IncidentDetails/GetFireIncidentPreview?getNotes=true&incidentNumber={incident_number}"
    
    payload = {}
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
        'Connection': 'keep-alive',
        'Cookie': eastcomm_cookie,
        'Referer': 'http://webcad.ehcec.net/index.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    
    response = requests.request("GET", url, headers=headers, data=payload)
    return response.json()

def getActiveIncidents():
    url = "http://webcad.ehcec.net/Incidents/GetFireActiveIncidents"
    logging.debug('Fetching active incidents')

    payload={}
    headers = {
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
      'Connection': 'keep-alive',
      'Cookie': eastcomm_cookie,
      'Referer': 'http://webcad.ehcec.net/index.html',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    logging.debug('Sending active incidents request')
    response = requests.request("POST", url, headers=headers, data=payload)
    json_results = response.json()
    logging.debug('Received active incidents response')
    return json_results

def prepare_quickbase_record(incident_data):
    """Prepare incident data for QuickBase"""
    try:
        incident_data_dict = json.loads(incident_data)
        for key, value in incident_data_dict.items():
            if key in ['ReceivedDate', 'ShipDate', 'FirstDispatchDate']:
                if value:
                    try:
                        date_obj = datetime.strptime(value, "%m/%d/%y %H:%M:%S")
                        incident_data_dict[key] = date_obj.isoformat()
                    except (ValueError, TypeError) as e:
                        print(f"Error converting date for {key}: {e}")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

    qb_record = {
        "to": "bum7eger8",
        "data": [
            {
                "6": {"value": incident_data_dict.get('IncidentNumber')},
                "7": {"value": incident_data_dict.get('ReceivedDate')},
                "8": {"value": incident_data_dict.get('ShipDate', '2024-11-14T17:20:18')},
                "9": {"value": incident_data_dict.get('FirstDispatchDate')},
                "12": {"value": incident_data_dict.get('Nature')},
                "13": {"value": incident_data_dict.get('Location', {}).get('Address', '7701 Wilshire Place')},
                "20": {"value": incident_data_dict.get('Location', {}).get('CrossStreet1')},
                "21": {"value": incident_data_dict.get('Location', {}).get('CoordinateX')},
                "22": {"value": incident_data_dict.get('Location', {}).get('CoordinateY')},
                "23": {"value": incident_data_dict.get('Location', {}).get('City')},
                "24": {"value": incident_data_dict.get('Location', {}).get('ZIP', '77000')},
                "25": {"value": incident_data_dict.get('Location', {}).get('FireAreaCode')},
                "26": {"value": incident_data_dict.get('Location', {}).get('LawJurisdictionCode')}
            }
        ],
        "fieldsToReturn": [6, 7, 8, 9, 12, 13, 20, 21, 22, 23, 24, 25, 26]
    }
    return qb_record

def create_quickbase_record(qb_record):
    """Create record in QuickBase"""
    qb_payload = json.dumps(qb_record)
    
    response = requests.post('https://api.quickbase.com/v1/records', headers=QB_HEADERS, json=qb_payload)
    response.raise_for_status()
    return response.json()

def update_incident_lifecycle(incident_number):
    """Update incident lifecycle to 6 in database"""
    conn = sqlite3.connect('incidents.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE incidents SET life_cycle = 6 WHERE incident_number = ?', 
                  (incident_number,))
    conn.commit()
    conn.close()

def process_closed_incidents():
    """Main function to process all closed incidents"""
    logging.info('Starting to process closed incidents')
    
    try:
        # Get closed incidents
        closed_incidents = get_closed_incidents_from_db()
        
        for incident_number in closed_incidents:
            try:
                # Get incident details
                incident_data = getClosedIncident(incident_number)
                
                # Prepare QuickBase record
                qb_record = prepare_quickbase_record(incident_data)
                print('Created the QB record')
                # Create record in QuickBase
                create_quickbase_record(qb_record)
                print('uploaded the QB record')
                # Update incident lifecycle
                update_incident_lifecycle(incident_number)
                print('updated the local DB record.')
                logging.info(f'Successfully processed incident {incident_number}')
                
            except Exception as e:
                logging.error(f'Error processing incident {incident_number}: {str(e)}')
                continue
                
    except Exception as e:
        logging.error(f'Error in process_closed_incidents: {str(e)}')
        raise

def main():
    logging.info('Starting main application loop')
    # Initialize connection to SQLite database
    QB_HEADERS, conn, cursor = setup()  # Capture the returned connection objects
    eastcommtoken()

    while True:
        try:
            logging.debug('Starting new iteration of main loop')
            # Get active incidents
            incidents = getActiveIncidents()
            logging.debug(f'Retrieved {len(incidents)} active incidents')
            
            # Filter and process ARS incidents
            for incident in incidents:
                if incident.get('NatureCode') == 'ARS':
                    incident_number = incident.get('IncidentNumber')
                    logging.debug(f'Processing ARS incident: {incident_number}')
                    
                    # Check if incident exists in database
                    cursor.execute('SELECT incident_number FROM incidents WHERE incident_number = ?', 
                                 (incident_number,))
                    exists = cursor.fetchone()
                    
                    if not exists:
                        cursor.execute('INSERT INTO incidents (incident_number, life_cycle, naturecode) VALUES (?, 1, ?)',
                                     (incident_number, incident.get('NatureCode')))
                        conn.commit()
                        logging.info(f'New ARS incident added: {incident_number}')
            
            # Update lifecycle for completed incidents
            cursor.execute('SELECT incident_number FROM incidents WHERE life_cycle < 5')
            db_incidents = cursor.fetchall()
            active_incident_numbers = [inc.get('IncidentNumber') for inc in incidents]
            
            for (db_incident_number,) in db_incidents:
                if db_incident_number not in active_incident_numbers:
                    cursor.execute('UPDATE incidents SET life_cycle = 5 WHERE incident_number = ?',
                                 (db_incident_number,))
                    conn.commit()
            
            # Process closed incidents
            process_closed_incidents()
            
            # Wait before next iteration
            time.sleep(2)
            
        except Exception as e:
            logging.error(f'Error in main loop: {str(e)}', exc_info=True)
            time.sleep(30)
            continue

if __name__ == "__main__":
    main()
