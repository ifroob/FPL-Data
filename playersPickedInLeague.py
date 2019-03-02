import requests
import json
import csv
import sys
import argparse
from time import gmtime, strftime
import xlsxwriter
import random
import linecache


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


def getJSONResponseFrom(url):
	jsonResponse = requests.get(url).json()
	return jsonResponse

def getLeagueInfo(leagueID, leagueStandingUrl) :
	leagueURL = leagueStandingUrl + str(leagueID) 
	jsonResponse = requests.get(leagueURL).json()
	#print jsonResponse
	leagueName = jsonResponse["league"]["name"]
	return leagueName

# Download all player data: https://fantasy.premierleague.com/drf/bootstrap-static
def getPlayersInfo():
    jsonResponse = requests.get(PLAYERS_INFO_URL).json()
    with open(PLAYERS_INFO_FILENAME, 'w') as outfile:
        json.dump(jsonResponse, outfile)

# Read player info from the downloaded file
def getAllPlayersDetailedJson():
    getPlayersInfo()
    with open(PLAYERS_INFO_FILENAME) as json_data:
        d = json.load(json_data)
        return d

def getPlayerNamesFromIds():
	allPlayers = getAllPlayersDetailedJson()
	playerElementIdToNameMap = {}
	for element in allPlayers["elements"]:
		playerName = element["second_name"] + ", " + element["first_name"]
		playerElementIdToNameMap[element["id"]] = playerName.encode("utf_8")
	return playerElementIdToNameMap
	
# Get users in league: https://fantasy.premierleague.com/drf/leagues-classic-standings/336217?phase=1&le-page=1&ls-page=5
def getUserIDs(leagueID, pageNumber, leagueStandingURL):
	# Get the URL from the PRESENT league standings.  This causes a problem whenever new users come into the league later on
    # https://fantasy.premierleague.com/a/leagues/standings/153201/classic?phase=1&lsPage=2&lePage=1
    # https://fantasy.premierleague.com/a/leagues/standings/153201/classic?phase=1&lsPage=3&lePage=1
	leagueURL = leagueStandingURL + str(leagueID) + "?phase=1&le-page=1&" + "ls-page=" + str(pageNumber)
	print (leagueURL)
	jsonResponse = requests.get(leagueURL).json()
	leagueStandings = jsonResponse["standings"]["results"]
	print(f"League Standings: {leagueStandings}") 
	if not leagueStandings:
		print("\nSuccess: Finished looking through all of the standings!")
		return None

	entries = []
	for player in leagueStandings:
		playerIsNotNew = player["last_rank"] # JSON field indicating if a player wasn't in the league before
		print (playerIsNotNew) 
		if (playerIsNotNew):
			print ("Entrant " + player["player_name"] + ": " + player["entry_name"])
			entries.append(player["entry"])

	return entries

# team picked by user. example: https://fantasy.premierleague.com/drf/entry/2677936/event/1/picks with 2677936 being entry_id of the player
# takes in a user entry id and gets their team
def getParticipantsTeamForGameweek(entry_id, GWNumber):    
	try:
		eventSubUrl = "event/" + str(GWNumber) + "/picks"
		playerTeamUrlForSpecificGW = FPL_URL + TEAM_ENTRY_SUBURL + str(entry_id) + "/" + eventSubUrl
		print(f"PLAYER TEAM CHOISE: {playerTeamUrlForSpecificGW} *********************")
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

	except ValueError:
    	# Maybe we can do something here where we exclude the team in which it fails on
	    print ("Decoding failed on " + str(entry_id))  
    	# print 'Exiting because decoding JSON has failed on team ' + str(entry_id)
    	# sys.exit()

def getTeamFrom(playerEntries, footballPlayers, GWNumber):
	playersPicked = {}
	captainsPicked = {}
	for entry in playerEntries:
		elements, captainId = getParticipantsTeamForGameweek(entry, GWNumber)
		print(f"Entry {entry} has {footballPlayers[captainId]} as captain")
		for element in elements:
			playerName = footballPlayers[element]
			if playerName in playersPicked:
				playersPicked[playerName] += 1
			else:
				playersPicked[playerName] = 1

		captainName = footballPlayers[captainId]
		if captainName in captainsPicked:
			captainsPicked[captainName] += 1
		else:
			captainsPicked[captainName] = 1
	return playersPicked, captainsPicked

# writes the results to csv file
def writeToFile(playersList, fileName):
	with open(fileName, 'w') as out:        
		csv_out = csv.writer(out)
		if "Players" in fileName:
			csv_out.writerow(['Players'])
		elif "Captains" in fileName:
			csv_out.writerow(['Captains'])
		csv_out.writerow(['Name', 'Times Picked'])        
		for row in playersList:
			csv_out.writerow(row)

# Main Script
def main():
	parser = argparse.ArgumentParser(description='Get players picked in your league in a certain GameWeek')
	print ("\n" + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + "\n")
	
	# 517116
	# leagueID = input("Enter League ID (e.g. 517116): ")
	leagueID = 517116
	# 1
	# gameweek = input("Enter GW number (e.g. 2): ")
	gameweek = 28
	# classic
	# leagueType  = input("Enter league type (classic or h2h): ")
	leagueType = "classic"

	# Dictionary of all premier league players {playerID, playerName}
	playerElementIdToNameDict = getPlayerNamesFromIds()

	totalNumberOfPlayersCount = 0
	pageCount = 1

	if leagueType == "h2h":
	    leagueStandingUrl = FPL_URL + LEAGUE_H2H_STANDING_SUBURL
	    print("H2H league")
	else:
	    leagueStandingUrl = FPL_URL + LEAGUE_CLASSIC_STANDING_SUBURL
	    print("Classic league mode")

	leagueName = getLeagueInfo(leagueID, leagueStandingUrl)
	print ("\n\t\t" + leagueName + "\n")

	# Grab data from the full link as specified
	# If there's multiple pages of participants in a league then that may need to be handled.
	while (True):
		try:
			playerEntries = getUserIDs(leagueID, pageCount, leagueStandingUrl)
			print (playerEntries)	        
			if (not playerEntries):
				break	        
			totalNumberOfPlayersCount += len(playerEntries)	       
			print("\npageCount: " + str(pageCount) + " total number of players: " + str(totalNumberOfPlayersCount))	       	        
	        
			# Get team for each entrant
			participantPlayers, participantCaptains = getTeamFrom(playerEntries, playerElementIdToNameDict, gameweek)
			
			# print("Participant's Players: \n", participantPlayers)
			# print("\nParticipant's Captains: \n", participantCaptains)
			
			sortedParticipantPlayersList = sorted(participantPlayers.items(), key=lambda x: x[1], reverse=True)
			sortedParticipantCaptainsList = sorted(participantCaptains.items(), key=lambda x: x[1], reverse=True)

			writeToFile(sortedParticipantCaptainsList, "GW " + str(gameweek) + " Captains Picked " + leagueName + ".csv")
			writeToFile(sortedParticipantPlayersList, "GW " + str(gameweek) + " Players Picked " + leagueName + ".csv")
			
			pageCount += 1

		except:
			exc_type, exc_obj, tb = sys.exc_info()
			f = tb.tb_frame
			lineno = tb.tb_lineno
			filename = f.f_code.co_filename
			linecache.checkcache(filename)
			line = linecache.getline(filename, lineno, f.f_globals)
			print ('EXCEPTION IN ({}, LINE {} "{}"): {}').format(filename, lineno, line.strip(), exc_obj)
			break

# Start
if __name__ == '__main__':
	main()
