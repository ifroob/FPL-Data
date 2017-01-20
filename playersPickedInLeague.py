import requests
import json
import csv
import sys
import argparse
from time import gmtime, strftime

import xlsxwriter
import random


FPL_URL = "https://fantasy.premierleague.com/drf/"
USER_SUMMARY_SUBURL = "element-summary/"
LEAGUE_CLASSIC_STANDING_SUBURL = "leagues-classic-standings/"
LEAGUE_H2H_STANDING_SUBURL = "leagues-h2h-standings/"
TEAM_ENTRY_SUBURL = "entry/"
PLAYERS_INFO_SUBURL = "bootstrap-static"
PLAYERS_INFO_FILENAME = "allPlayersInfo.json"

USER_SUMMARY_URL = FPL_URL + USER_SUMMARY_SUBURL
PLAYERS_INFO_URL = FPL_URL + PLAYERS_INFO_SUBURL
START_PAGE = 1


def getLeagueInfo(league_id,league_Standing_Url) :
	league_url = league_Standing_Url + str(league_id) 
	r = requests.get(league_url)
	jsonResponse = r.json()
	#print jsonResponse
	leagueName = jsonResponse["league"]["name"]
	return leagueName


# Download all player data: https://fantasy.premierleague.com/drf/bootstrap-static
def getPlayersInfo():
    r = requests.get(PLAYERS_INFO_URL)
    jsonResponse = r.json()
    with open(PLAYERS_INFO_FILENAME, 'w') as outfile:
        json.dump(jsonResponse, outfile)


# Get users in league: https://fantasy.premierleague.com/drf/leagues-classic-standings/336217?phase=1&le-page=1&ls-page=5
def getUserEntryIds(league_id, ls_page, league_Standing_Url):
	# Get the URL from the PRESENT league standings.  This causes a problem whenever new users come into the league later on
    league_url = league_Standing_Url + str(league_id) + "?phase=1&le-page=1&ls-page=" + str(ls_page)
    # print league_url
    r = requests.get(league_url)
    jsonResponse = r.json()
    print jsonResponse
    standings = jsonResponse["standings"]["results"]
    
    if not standings:
        print("\nSuccess: Finished looking through all of the standings!")
        return None

    entries = []

    # print standings
    i = 1

    for player in standings:
    	isNew = player["last_rank"] # JSON field indicating if a player wasn't in the league before
        print isNew 
        if (isNew != 0) :
	        print (str(i) + ") " + player["player_name"] + ": " + player["entry_name"])
	        entries.append(player["entry"])
	        i = i + 1

    return entries


# team picked by user. example: https://fantasy.premierleague.com/drf/entry/2677936/event/1/picks with 2677936 being entry_id of the player
# takes in a user entry id and gets their team
def getplayersPickedForEntryId(entry_id, GWNumber):
    
    try :		    
	    eventSubUrl = "event/" + str(GWNumber) + "/picks"
	    playerTeamUrlForSpecificGW = FPL_URL + TEAM_ENTRY_SUBURL + str(entry_id) + "/" + eventSubUrl
	    r = requests.get(playerTeamUrlForSpecificGW)
	    jsonResponse = r.json()
	    picks = jsonResponse["picks"]
	    elements = []
	    captainId = 1
	    for pick in picks:
	        elements.append(pick["element"])
	        if pick["is_captain"]:	
	            captainId = pick["element"]
	    
	    return elements, captainId

    except ValueError :
    	# Maybe we can do something here where we exclude the team in which it fails on
	    print 'Decoding failed on ' + str(entry_id)  
    	# print 'Exiting because decoding JSON has failed on team ' + str(entry_id)
    	# sys.exit()


# read player info from the json file that we downlaoded
def getAllPlayersDetailedJson():
    with open(PLAYERS_INFO_FILENAME) as json_data:
        d = json.load(json_data)
        return d

# writes the results to csv file
def writeToFile(countOfplayersPicked, fileName):
    with open(fileName, 'w') as out:
        
        csv_out = csv.writer(out)
        
        if len(countOfplayersPicked) == len(countOfCaptainsPicked) :
        	csv_out.writerow(['Captains'])
        else :
        	csv_out.writerow([' '])
        	csv_out.writerow(['Players'])

        csv_out.writerow(['Name', '# Times Picked'])
        
        for row in countOfplayersPicked:
            # print row
            csv_out.writerow(row)

# Main Script

parser = argparse.ArgumentParser(description='Get players picked in your league in a certain GameWeek')
#parser.add_argument('-l','--league', help='league entry id', required=True)
#parser.add_argument('-gw','--gameweek', help='gameweek number', required=True)
#parser.add_argument('-t', '--type', help='league type')

print "\n" + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + "\n"
league = raw_input("Enter League ID (e.g. 5320): ")
gameweek = raw_input("Enter GW number (e.g. 2): ")
type = raw_input("Enter league type (classic or h2h): ")
#args = vars(parser.parse_args())

getPlayersInfo()
playerElementIdToNameMap = {}
allPlayers = getAllPlayersDetailedJson()
for element in allPlayers["elements"]:
    playerElementIdToNameMap[element["id"]] = element["web_name"].encode('ascii', 'ignore')

countOfplayersPicked = {}
countOfCaptainsPicked = {}
totalNumberOfPlayersCount = 0
pageCount = START_PAGE
GWNumber = gameweek
leagueIdSelected = league

if type == "h2h":
    leagueStandingUrl = FPL_URL + LEAGUE_H2H_STANDING_SUBURL
    print("H2H league")
else:
    leagueStandingUrl = FPL_URL + LEAGUE_CLASSIC_STANDING_SUBURL
    print("Classic league mode")

leagueName = getLeagueInfo(leagueIdSelected, leagueStandingUrl)
print "\n\t\t" + leagueName + "\n"

# Grab data from the full link as specified
while (True):
    try:
        entries = getUserEntryIds(leagueIdSelected, pageCount, leagueStandingUrl)
        # print entries
        if entries is None:
     		# no more players to look at
            break

        totalNumberOfPlayersCount += len(entries)
        print("\npageCount: " + str(pageCount) + " total number of players: " + str(totalNumberOfPlayersCount))
        
        # Goes through each player id and finds team

        for entry in entries:
            elements, captainId = getplayersPickedForEntryId(entry, GWNumber)
            for element in elements:
                name = playerElementIdToNameMap[element]
                if name in countOfplayersPicked:
                    countOfplayersPicked[name] += 1
                else:
                    countOfplayersPicked[name] = 1

            captainName = playerElementIdToNameMap[captainId]
            if captainName in countOfCaptainsPicked:
                countOfCaptainsPicked[captainName] += 1
            else:
                countOfCaptainsPicked[captainName] = 1

        

        listOfCountOfCaptainsPicked = sorted(countOfCaptainsPicked.items(), key=lambda x: x[1], reverse=True)
        listOfcountOfplayersPicked = sorted(countOfplayersPicked.items(), key=lambda x: x[1], reverse=True)

        writeToFile(listOfCountOfCaptainsPicked, "GW " + str(GWNumber) + " CaptainsPicked " + leagueName + ".csv")
        writeToFile(listOfcountOfplayersPicked, "GW " + str(GWNumber) + " PlayersPicked " + leagueName + ".csv")


       	#writeToFile(listOfCountOfCaptainsPicked, "file.xlsx")

        pageCount += 1

    except Exception as e:
        print 'Exception Caught'
        print(e)
        pass
