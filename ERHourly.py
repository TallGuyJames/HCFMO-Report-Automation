# %% [markdown]
# This script runs hourly to cleanup the current set and send reminders. 

# %%
import requests
import json
import smtplib
import time
import dateutil.parser as dp
from hcfmosecrets import *
from email.message import EmailMessage


smtp_server = smtplib.SMTP(smtp_address)
allexposuresURL = 'https://data.emergencyreporting.com/agencyincidents/incidents/exposures'
getuserURL = 'https://data.emergencyreporting.com/agencyusers/users/'
tokenexpiration = 1653785837
summarybody = ""

def summaryemail(text):
    global summarybody
    summarybody += text
    summarybody += '\n'
    return

def getincompleteincidents():
    checktoken()
    exposures = []
    exposures_offset = 0
    response = requests.get(allexposuresURL + "?filter=completedByUserID eq null", headers=requestheaders)
    r = response.json()

    #append exposures into exposures list
    while len(r['exposures']) != 0:
        for each in r['exposures']:
            e = { "incidentID": each['incidentID'], "shiftsOrPlatoon": each['shiftsOrPlatoon'], "incidentType": each['incidentType'],  "assignedToUserID": each['assignedToUserID'], "primaryActionTaken": each['primaryActionTaken'], "secondaryActionTaken": each['secondaryActionTaken'], "thirdActionTaken": each['thirdActionTaken'], "completedByUserID": each['completedByUserID'], "reviewedByUserID": each['reviewedByUserID'], "completedDateTime": each['completedDateTime'], "reviewedDateTime": each['reviewedDateTime'], "psapDateTime": each['psapDateTime'], "dispatchNotifiedDateTime": each['dispatchNotifiedDateTime'], "initialResponderDateTime": each['initialResponderDateTime'], "hasPropertyLoss": each['hasPropertyLoss'], "propertyLossAmount": each['propertyLossAmount'], "hasContentLoss": each['hasContentLoss'], "contentLossAmount": each['contentLossAmount'], "hasPreIncidentPropertyValue": each['hasPreIncidentPropertyValue'], "preIncidentPropertyValueAmount": each['preIncidentPropertyValueAmount'], "hasPreIncidentContentsValue": each['hasPreIncidentContentsValue'], "preIncidentContentsValueAmount": each['preIncidentContentsValueAmount'], "complaintReportedByDispatch": each['complaintReportedByDispatch'], "exposureID": each['exposureID'], "rowVersion": each['rowVersion'] }
            exposures.append(e)
        exposures_offset += 10
        offsetURL = allexposuresURL+"?offset="+str(exposures_offset)+"&filter=completedByUserID eq null"
        response = requests.get(offsetURL, headers=requestheaders)
        r = response.json() 
    return exposures

def getincidentdata(incidentID): 
    checktoken()
    resp = requests.get('https://data.emergencyreporting.com/agencyincidents/incidents/' + incidentID,
                        headers=requestheaders)
    response = resp.json()
    incidentData = { 'incidentDateTime': response["incident"]["incidentDateTime"], 'incidentNumber': response["incident"]["incidentNumber"], 'dispatchRunNumber': response["incident"]["dispatchRunNumber"],'rowVersion': response["incident"]["rowVersion"] }
    return incidentData

def checkforphoneconsult(dispatchRun): 
    checktoken()
    resp = requests.get('https://data.emergencyreporting.com/agencyincidents/incidents?filter=dispatchRunNumber eq ' + dispatchRun,
                        headers=requestheaders)
    response = resp.json()
    if len(response['incidents']) == 1:
        incidentData = [response["incidents"][0]["incidentID"],response["incidents"][0]["dispatchRunNumber"],response["incidents"][0]["isComplete"]]
        return incidentData
    return

def deleteincident(incidentID):
    checktoken()
    resp = requests.delete('https://data.emergencyreporting.com/agencyincidents/incidents/' + incidentID,
                        headers=requestheaders)
    print("deleted incident " + incidentID)
    return

def getLocation(exposureID):
    checktoken()
    resp = requests.get('https://data.emergencyreporting.com/agencyincidents/exposures/' + exposureID + '/location',
                        headers=requestheaders)
    response = resp.json()
    location = response["exposureLocation"]["milePostNumber"] + " " + response["exposureLocation"]["streetPrefix"] + " " + response["exposureLocation"]["streetName"] + " " + response["exposureLocation"]["streetType"] + " " + response["exposureLocation"]["streetSuffix"]
    print('location data:')
    print(response)
    return location

def getUser(userID):
    resp = requests.get('https://data.emergencyreporting.com/agencyusers/users/'+ userID,headers=requestheaders)
    response = resp.json()
    name = response["user"]["fullName"]
    email = response["user"]["email"]
    rtn = [name, email]
    return rtn

def getUserByUnit(unitNumber):
    resp = requests.get('https://data.emergencyreporting.com/agencyusers/users?filter=agencyPersonnelID eq '+ unitNumber,headers=requestheaders)
    response = resp.json()
    user = { 'userID': response["users"][0]["userID"], 'email': response["users"][0]["email"] }
    return user

def getjotformphoneconsult():
    resp = requests.get('https://api.jotform.com/form/70595662945166/submissions?apiKey='+jotform_api_key+'&limit=75')
    response = resp.json()
    summaryemail('Pulled JotForm data')
    return response['content']

def refreshtoken():
    global requestheaders
    global tokenexpiration
    global key
    global token
    tokenURL = 'https://login.microsoftonline.com/login.emergencyreporting.com/oauth2/v2.0/token'
    key = ER_token
    tokenbody = {
        "grant_type":"client_credentials",
        "client_id": ER_client_id,
        "client_secret": ER_client_secret,
        "scope":"https://login.emergencyreporting.com/secure/.default offline_access"
    }
    tokenheaders = {
    'content-type':'application/x-www-form-urlencoded'
    }
    # request token
    tokenresponse = requests.post(tokenURL,data=tokenbody,headers=tokenheaders)

    #place token and key for future use
    tokenresponsejson = tokenresponse.json()
    token = tokenresponsejson["access_token"]
    tokenexpiration = time.time()+3599
    requestheaders = {
        "Authorization": token,
        "Ocp-Apim-Subscription-Key":key,
        "Cache-Control": "no-cache"
    }

def checktoken():
    if tokenexpiration < time.time():
        refreshtoken()
        
def deletephoneconsults():
    #clear phone consult list
    phoneconsultlist = []
    jotformdata = getjotformphoneconsult()

    #for each phone consult, look for a valid incidentID, then add to list
    for each in jotformdata:
        if len(each['answers']['64']['answer']) != 9:
            print('does not equal 9')
        phoneconsultlist.append(each['answers']['64']['answer'])

    #pull incidents
    for each in phoneconsultlist:
        incidentdata = checkforphoneconsult(each)
        #found incident, delete it
        if incidentdata != None:
            if incidentdata[2] == '0':
                deleteincident(incidentdata[0])
                summaryemail('deleted phone consult')
                
def getonsapparatuses(exposureID):
    checktoken()
    resp = requests.get('https://data.emergencyreporting.com/agencyincidents/exposures/' + exposureID + '/apparatuses?filter=arrivedDateTime ne null',
                        headers=requestheaders)
    response = resp.json()
    return response

def getapparatuses(exposureID):
    checktoken()
    resp = requests.get('https://data.emergencyreporting.com/agencyincidents/exposures/' + exposureID + '/apparatuses?filter=arrivedDateTime eq null',
                        headers=requestheaders)
    response = resp.json()
    return response

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


# %%

# delete phone consults
deletephoneconsults()
summaryemail('Deleting Phone Consults')

#delete follow ups
exposures = getincompleteincidents()
summaryemail('Pulled incomplete incidents')

#deletes 555 which is a follow up and 911 which is inspections
for each in exposures:
    if each['incidentType'] == '555':
        print('Deleting 555 incident ')
        summaryemail('Deleted a follow up')
        deleteincident(each['incidentID'])
    elif each['incidentType'] == '911':
        print('Deleting 911 incident')
        deleteincident(each['incidentID'])

# %%
#refresh incomplete after deleting
exposures = getincompleteincidents()

#assigned unassigned calls and set station
print('There are '+ str(len(exposures)) + ' exposures to review')
count = 0
for each in exposures:
    count += 1
    print('Working on record ' + str(count) + ' of ' + str(len(exposures)))
    summaryemail('Working on record ' + str(count) + ' of ' + str(len(exposures)))
    #looks for investigations calls that are not assigned
    if each['incidentType'] == '100' and each['assignedToUserID'] == None:
        print('pulled unassigned incident')
        summaryemail('Found incident that is Investigations and not assigned')

        ##Future, check CAD for active incident

        ##pull the apparatus assigned to this incident
        apparatus = getonsapparatuses(each['exposureID'])

        #check to see if there is an apparatus
        if len(apparatus['exposureApparatuses']) != 0:
            print('at least one apparatus')
            print(apparatus['exposureApparatuses'][0]['agencyApparatusID'])
            if dp.parse(apparatus['exposureApparatuses'][0]['arrivedDateTime']).timestamp() < time.time() - 100:
                #pull data
                user_return = getUserByUnit(apparatus['exposureApparatuses'][0]['agencyApparatusID'])
                apparatus = getonsapparatuses(each['exposureID'])
                incidentdata = getincidentdata(each['incidentID'])
                print('Looking at incident 2022-' + incidentdata['incidentNumber'])
                summaryemail('Looking at incident 2022-' + incidentdata['incidentNumber'])
                #set headers
                incidentPATCHheaders = {
                    "Authorization": token,
                    "Ocp-Apim-Subscription-Key":key,
                    "Cache-Control": "no-cache",
                    "Etag": incidentdata['rowVersion']
                }
                exposurePATCHheaders = {
                    "Authorization": token,
                    "Ocp-Apim-Subscription-Key":key,
                    "Cache-Control": "no-cache",
                    "Etag": each['rowVersion']
                }

                #set data
                print('setting incident data for 2022-0' + incidentdata['dispatchRunNumber'][-5:])
                summaryemail('setting incident data for 2022-0' + incidentdata['dispatchRunNumber'][-5:])
                incidentPATCHdata = {
                    'stationID': '20868',
                    'fdid': 'x1870',
                    'incidentNumber': '0' + incidentdata['dispatchRunNumber'][-5:]
                }

                exposurePATCHdata = {
                    'shiftsOrPlatoon': 'Investigations',
                    'assignedToUserID': user_return['userID'],
                    'primaryActionTaken': '86'
                }
                #issue commands
                patch = requests.patch('https://data.emergencyreporting.com/agencyincidents/incidents/' + each['incidentID'], data = incidentPATCHdata, headers=incidentPATCHheaders) 
                summaryemail(str(patch))
                results = patch.json()

                patch = requests.patch('https://data.emergencyreporting.com/agencyincidents/incidents/' + each['incidentID'] + '/exposures/' + each['exposureID'], data = exposurePATCHdata, headers=exposurePATCHheaders) 
                summaryemail(str(patch))
                results = patch.json()
                print('assigned incident 2022-' + incidentPATCHdata['incidentNumber'])
                summaryemail('assigned incident 2022-' + incidentPATCHdata['incidentNumber'])
        else:
            try:
                #get incident and location data
                incidentdata = getincidentdata(each['incidentID'])
                location = getLocation(each['exposureID'])
                if incidentdata['incidentDateTime'][-12:] == '00:00:00.000':
                    msgContent = 'The Investigator who picked up incident (2022-' + incidentdata['incidentNumber'] + ') at ' + location + ' on ' + incidentdata['incidentDateTime'] + ' failed to add themselves to the call. The phone consult is missing.'
                    message = EmailMessage()
                    message.set_content(msgContent)
                    message['Subject'] = 'Missing Investigator'
                    message['From'] = 'noreply@fmo.hctx.net'
                    message['To'] = 'james.singleton@fmo.hctx.net'
                    smtp_server.send_message(message)
                    print('emailed incident with no unit')
                    summaryemail('emailed incident with no unit')
            except:
                try:
                    if dp.parse(each['psapDateTime']).timestamp() < time.time() - 14400:
                        summaryemail('emailing an error in automation')
                        msgContent = 'There was an error while handling hourly automation. See the below report'
                        msgContent += '\n'
                        msgContent += 'Working on record ' + str(count) + ' of ' + str(len(exposures))
                        msgContent += '\n'
                        msgContent += incidentdata['dispatchRunNumber']

                        message = EmailMessage()
                        message.set_content(msgContent)
                        message['Subject'] = 'Automation Error'
                        message['From'] = 'arsonsup@fmo.hctx.net'
                        message['To'] = 'james.singleton@fmo.hctx.net'

                        smtp_server.send_message(message)
                except:
                    summaryemail('error in a report')
                else:
                    summaryemail('error email averted')
                    msgContent = 'This would have been an email but I did not send since it is too close to call creation.'
                    msgContent += '\n'
                    msgContent += 'Working on record ' + str(count) + ' of ' + str(len(exposures))
                    msgContent += '\n'
                    msgContent += incidentdata['dispatchRunNumber']

                    message = EmailMessage()
                    message.set_content(msgContent)
                    message['Subject'] = 'Automation Error'
                    message['From'] = 'arsonsup@fmo.hctx.net'
                    message['To'] = 'james.singleton@fmo.hctx.net'

                    smtp_server.send_message(message)  
            else:
                #pull apparatus
                apparatus = getapparatuses(each['exposureID'])
                if dp.parse(apparatus['exposureApparatuses'][0]['dispatchDateTime']).timestamp() < time.time() - 14400:
                    user_return = getUserByUnit(apparatus['exposureApparatuses'][0]['agencyApparatusID'])
                    print('Looking at incident 2022-' + incidentdata['incidentNumber'])
                    #set headers
                    incidentPATCHheaders = {
                        "Authorization": token,
                        "Ocp-Apim-Subscription-Key":key,
                        "Cache-Control": "no-cache",
                        "Etag": incidentdata['rowVersion']
                    }
                    exposurePATCHheaders = {
                        "Authorization": token,
                        "Ocp-Apim-Subscription-Key":key,
                        "Cache-Control": "no-cache",
                        "Etag": each['rowVersion']
                    }
                    #set data
                    incidentPATCHdata = {
                        'stationID': '20868',
                        'fdid': 'x1870',
                        'incidentNumber': '0' + incidentdata['dispatchRunNumber'][-5:]
                    }
                    exposurePATCHdata = {
                        'shiftsOrPlatoon': 'Investigations',
                        'assignedToUserID': user_return['userID'],
                        'primaryActionTaken': '86'
                    }
                    #issue commands
                    patch = requests.patch('https://data.emergencyreporting.com/agencyincidents/incidents/' + each['incidentID'], data = incidentPATCHdata, headers=incidentPATCHheaders) 
                    results = patch.json()
                    patch = requests.patch('https://data.emergencyreporting.com/agencyincidents/incidents/' + each['incidentID'] + '/exposures/' + each['exposureID'], data = exposurePATCHdata, headers=exposurePATCHheaders) 
                    results = patch.json()
                    print('assigned incident')
                    summaryemail('assigned incident ' + incidentPATCHdata['incidentNumber'])

                    user = getUserByUnit(apparatus['exposureApparatuses'][0]['agencyApparatusID'])
                    #pull incident data
                    incidentdata = getincidentdata(each['incidentID'])
                    #send email to offender
                    #print('The system cannot find a phone consult for your incident (2022-' + incidentdata['incidentNumber'] + ') at ' + location + '. Please complete the phone consult or contact your supervisor.')
                    msgContent = 'The system cannot find a phone consult for your incident (2022-' + incidentdata['incidentNumber'] + ') at ' + location + ' on ' + incidentdata['incidentDateTime'] + '. Please complete the phone consult or contact your supervisor.'
                    message = EmailMessage()
                    message.set_content(msgContent)
                    message['Subject'] = 'Missing Phone Consult'
                    message['From'] = 'arsonsup@fmo.hctx.net'
                    message['To'] = user['email']
                    #message['To'] = 'james.singleton@fmo.hctx.net'
                    message['BCC'] = ['james.singleton@fmo.hctx.net']
                    smtp_server.send_message(message)
                    print('emailed missing phone consult')
                    summaryemail('emailed missing phone consult ' + user['email'])

                    
msgContent = summarybody
message = EmailMessage()
message.set_content(msgContent)
message['Subject'] = 'Hourly ER Log'
message['From'] = 'noreply@fmo.hctx.net'
message['To'] = 'james.singleton@fmo.hctx.net'
smtp_server.send_message(message)

# %%
#refresh incomplete after assigning
exposures = getincompleteincidents()

#This FOR section pulls incidents and corrects the incident number if it is short
summaryemail('Looking for invalid incident numbers')
for each in exposures:
    if each['incidentType'] == '100': #could this be station 2 instead???
        incidentdata = getincidentdata(each['incidentID'])
        print(incidentdata)
        if len(incidentdata['incidentNumber']) == 5:
            print('Short incident number ' + incidentdata['incidentNumber'])
            summaryemail('Found an error in ' + incidentdata['incidentNumber'])
            incidentPATCHheaders = {
                "Authorization": token,
                "Ocp-Apim-Subscription-Key":key,
                "Cache-Control": "no-cache",
                "Etag": incidentdata['rowVersion']
            }
            incidentPATCHdata = {
                'stationID': '20868',
                'fdid': 'x1870',
                'incidentNumber': '0' + incidentdata['dispatchRunNumber'][-5:]
            }
            patch = requests.patch('https://data.emergencyreporting.com/agencyincidents/incidents/' + each['incidentID'], data = incidentPATCHdata, headers=incidentPATCHheaders) 
            print(patch)
            #summaryemail(patch)
            results = patch.json()
        else:
            print('Long incident number ' + incidentdata['incidentNumber'])

# %%



