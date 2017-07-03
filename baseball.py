# imports for the program
from bs4 import BeautifulSoup
import urllib.request
import pandas as pd
import numpy as np
import json
import time

'''
paramaters for 
cur_date: date of the games
pitchers_games: number of previous games for pitchers stats
batters_games: number of previous games for batters stats
teams_games: number of previous games for team stats
'''
cur_date = pd.to_datetime('today').date()
pitchers_games = 5
batters_games = 7
teams_games = 5

#main function
def get_stats(date,prev_pit,prev_bat,prev_team):

	#creates a connection to get the lineups for all teams on the specified date
	r = urllib.request.urlopen('http://www.baseballpress.com/lineups/' + date).read()
	soup = BeautifulSoup(r,"lxml")
	
	# gets a list of all game div objects
	games = soup.find_all("div", { "class" : "game clearfix" })
	
	game_number = 1
	
	# prints the date
	print('Date:' + date)

	# for each game 
	for game in games:

		# prints the game number
		print("Game " + str(index))

		# finds the div objects for the home and away team
		teams = game.find_all("div", {"class" : "team-data"})
		
		# finds the div objects for the home and away lineups
		players = game.find_all("div", {"class" : "players"})
		
		# stores the teams as div objects
		home_team = teams[0]
		away_team = teams[1]
		
		# finds and stores the team names as strings
		home_name = home_team.find("div", {"class" : "team-name"}).text
		away_name = away_team.find("div", {"class" : "team-name"}).text
		
		# finds and stores the starting pitchers' names as strings
		home_pitch_name = home_team.find("a",{"class" : "player-link"}).text
		away_pitch_name = away_team.find("a",{"class" : "player-link"}).text
		
		# finds and stores the lineup elements for both teams
		home_lineup = players[0].find_all("a",{"class" : "player-link"})
		away_lineup = players[1].find_all("a",{"class" : "player-link"})
		
		# prints the game matchup
		print(home_name + ' vs. ' + away_name)
		
		# gets the team statistics for both teams
		# uses the try_x helper method to account for failed/busy connection 
		params = (home_name,prev_team)
		valid_home_summary,home_summary = try_x(team_stats,params,5)
		params = (away_name,prev_team)
		valid_away_summary,away_summary = try_x(team_stats,params,5)

		# gets the pitcher statistics for both starting pitchers
		# uses the try_x helper method to account for failed/busy connection 
		params = (home_pitch_name,prev_pit)
		valid_home_pitch,home_pitch = try_x(pitcher_stats,params,5)
		params = (away_pitch_name,prev_pit)
		valid_away_pitch,away_pitch = try_x(pitcher_stats,params,5)

		# if any of the team or pitchers' statistics not available continues to next game
		if not valid_home_summary or not valid_away_summary or not valid_home_pitch or not valid_away_pitch:
			print('\tData not available')
			continue
		
		# prints the home team's name and statistics
		print(home_name)
		print(home_summary)

		# prints the home pitcher's name and statistics
		print('\tPitcher: ' + home_pitch_name)
		print('\t\t' + str(home_pitch))

		# iterates through each batter in the home team's lineup
		for batter in home_lineup:

			# prints the name of the batter
			print('\tName: ' + batter.text)

			# gets the batter statistics for the given batter against the opponents pitching arm
			# uses the try_x helper method to account for failed/busy connection 
			params = (batter.text,prev_bat,away_pitch['throws'])
			valid,summary = try_x(batter_stats,params,5)

			# if stats not valid prints error message and continues to next batter
			if not valid:
				print('\t\t' + summary)
				continue

			# prints the batter's statistics
			last_x,vs = summary
			print('\t\t' + str(last_x))
			print('\t\t' + str(vs))

		# prints the away team's name and statistics
		print(away_name)
		print(away_summary)

		# prints the away pitcher's name and statistics
		print('\tPitcher: ' + away_pitch_name)
		print('\t\t' + str(away_pitch))
	
		# iterates through each batter in the home team's lineup
		for batter in away_lineup:

			# prints the name of the batter
			print('\tName: ' + batter.text)

			# gets the batter statistics for the given batter against the opponents pitching arm
			# uses the try_x helper method to account for failed/busy connection 
			params = (batter.text,prev_bat,home_pitch['throws'])
			valid, summary = try_x(batter_stats,params,5)

			# if stats not valid prints error message and continues to next batter
			if not valid:
				print('\t\t' + summary)
				continue

			# prints the batter's statistics
			last_x,vs = summary
			print('\t\t' + str(last_x))
			print('\t\t' + str(vs))

		#updates the game number
		game_number += 1

# queries stats for a given pitcher, returns averages over prev_games games 
def pitcher_stats(name,prev_games):

	# normalizes the name to makes sure it's recognized by database
	name = normalize(name)

	# SDQL query for pitcher stats
	# for more information go to http://sportsdatabase.com/mlb/pitcher_query
	SDQL = 'starter throws,innings pitched,runs allowed,hits allowed,batters faced,strike outs thrown,walks allowed,result,date@name=' + name + ' and date<' + str(to_integer(cur_date))
	
	# converts the english querry into http version
	query = pitcher_query(SDQL)
	
	# makes an http request for the query and stores the resulting response
	request = urllib.request.Request(query,headers={'User-Agent': 'Mozilla/5.0'})
	response = urllib.request.urlopen(request)
	
	# converts the response into plain-text 
	data = response.read().decode('utf-8')
	
	# stores the data into a pandas dataframe, labels the columns by their respective column names
	data = data.replace('json_callback(','').replace(');','').replace('\'','\"')
	
	# converts the plain-text into a python dictionary
	data = json.loads(data)
	
	# stores the data into a pandas dataframe, labels the columns by their respective column names
	stats = pd.DataFrame(data['groups'][0]['columns']).T
	stats.columns = data['headers']
	
	# gets the last (most recent) rows from the dataframe
	prev = stats.tail(prev_games)
	
	summary = {}
	
	# if there are no rows returns empty dictionary
	if len(prev) > 0:

		# returns the batter averages/inning over the last games
		innings = float(sum(prev['innings pitched']))
		summary['throws'] = prev.iloc[0]['starter throws']
		summary['runs/i'] = format(sum(prev['runs allowed']) / innings,'.4f')
		summary['hits/i'] = format(sum(prev['hits allowed']) / innings,'.4f')
		summary['batters/i'] = format(sum(prev['batters faced']) / innings,'.4f')
		summary['ks/i'] = format(sum(prev['strike outs thrown']) / innings,'.4f')
		summary['bbs/i'] = format(sum(prev['walks allowed']) / innings,'.4f')
		summary['ob%'] = format((sum(prev['hits allowed']) + sum(prev['walks allowed'])) /sum(prev['batters faced']),'.4f')
		summary['wins/last' + str(prev_games)] = sum(prev['result'] == 'W')
		summary['last game'] = pd.to_datetime(str(prev.iloc[-1]['date']), format='%Y%m%d').date()
	
	return summary

# queries stats for a given batter, returns averages over prev_games games 
def batter_stats(name,prev_games,throws=''):

	# normalizes the name to makes sure it's recognized by database
	name = normalize(name)

	# SDQL query for batter stats
	# for more information go to http://sportsdatabase.com/mlb/batter_query
	SDQL = 'at bats,hits,doubles,triples,home runs,rbi,runs,walks,strike outs,o:starter throws,date@name=' + name + ' and date<' + str(to_integer(cur_date))
	
	# converts the english querry into http version
	query = batter_query(SDQL)

	# makes an http request for the query and stores the resulting response
	request = urllib.request.Request(query,headers={'User-Agent': 'Mozilla/5.0'})
	response = urllib.request.urlopen(request)

	# converts the response into plain-text 
	data = response.read().decode('utf-8')

	# removes the unnessary text and replaces single quotes with double quotes so the json file can be properlly parsed
	data = data.replace('json_callback(','').replace(');','').replace('\'','\"')
	
	# converts the plain-text into a python dictionary
	data = json.loads(data)
	
	# stores the data into a pandas dataframe, labels the columns by their respective column names
	stats = pd.DataFrame(data['groups'][0]['columns']).T
	stats.columns = data['headers']
	
	# gets the last (most recent) rows from the dataframe
	prev = stats.tail(prev_games)
	
	summary = {}
	
	# if there are no rows returns empty dictionary
	if len(prev) > 0:

		# returns the batter averages/at_bat over the last games
		at_bats = float(sum(prev['at bats']))
		summary['hits/ab'] = format(sum(prev['hits']) / at_bats,'.4f')
		summary['slugging'] = format((sum(prev['hits']) + sum(prev['doubles']) + (2 * sum(prev['triples'])) + (3 * sum(prev['home runs']))) / at_bats,'.4f')
		summary['rbis/ab'] = format(sum(prev['rbi']) / at_bats,'.4f')
		summary['runs/ab'] = format(sum(prev['runs']) / at_bats,'.4f')
		summary['ks/ab'] = format(sum(prev['strike outs']) / at_bats,'.4f')
		summary['bbs/ab'] = format(sum(prev['walks']) / at_bats,'.4f')
		summary['ob%'] = format((sum(prev['hits']) + sum(prev['walks'])) / at_bats,'.4f')
		summary['last game'] = pd.to_datetime(str(prev.iloc[-1]['date']), format='%Y%m%d').date()

	# gets the last (most recent) rows from the dataframe against a right/left handed pitcher
	prev_vs = stats[stats['o:starter throws'] == throws].tail(prev_games * 2)

	vs = {}

	# if there are no rows returns empty dictionary
	if len(prev_vs) > 0:

		# returns the batter averages/at_bat over the last games
		vs_at_bats = float(sum(prev_vs['at bats']))
		vs['vs'] = throws
		vs['hits/ab'] = format(sum(prev_vs['hits']) / vs_at_bats,'.4f')
		vs['slugging'] = format((sum(prev_vs['hits']) + sum(prev_vs['doubles']) + (2 * sum(prev_vs['triples'])) + (3 * sum(prev_vs['home runs']))) / vs_at_bats,'.4f')
		vs['rbis/ab'] = format(sum(prev_vs['rbi']) / vs_at_bats,'.4f')
		vs['runs/ab'] = format(sum(prev_vs['runs']) / vs_at_bats,'.4f')
		vs['ks/ab'] = format(sum(prev_vs['strike outs']) / vs_at_bats,'.4f')
		vs['bbs/ab'] = format(sum(prev_vs['walks']) / vs_at_bats,'.4f')
		vs['ob%'] = format((sum(prev_vs['hits']) + sum(prev_vs['walks'])) / vs_at_bats,'.4f')
		vs['last game'] = pd.to_datetime(str(prev_vs.iloc[-1]['date']), format='%Y%m%d').date()

	# if pitching not selected returns only summary dictionary, otherwise returns summary and vs dictionary
	if throws == '':
		return summary

	return summary,vs

# queries stats for a given team, returns averages over prev_games games 
def team_stats(name,prev_games):

	# SDQL query for team stats
	# for more information go to http://sportsdatabase.com/mlb/query
	SDQL = 'date,at bats,hits,runs,team left on base,errors,margin,streak@team=' + name + ' and date<' + str(to_integer(cur_date))
	
	# converts the english querry into http version
	query = team_query(SDQL)
	
	# makes an http request for the query and stores the resulting response
	request = urllib.request.Request(query,headers={'User-Agent': 'Mozilla/5.0'})
	response = urllib.request.urlopen(request)
	
	# converts the response into plain-text 
	data = response.read().decode('utf-8')

	# removes the unnessary text and replaces single quotes with double quotes so the json file can be properlly parsed
	data = data.replace('json_callback(','').replace(');','').replace('\'','\"')
	
	# converts the plain-text into a python dictionary
	data = json.loads(data)
	
	# stores the data into a pandas dataframe, labels the columns by their respective column names
	stats = pd.DataFrame(data['groups'][0]['columns']).T
	stats.columns = data['headers']
	
	# gets the last (most recent) rows from the dataframe
	prev = stats.tail(prev_games)

	summary = {}

	# if there are no rows returns empty dictionary
	if len(prev) > 0:
		# returns the team averages over the last games

		summary['at_bats/game'] = format(prev['at bats'].mean(),'.4f')
		summary['hits/game'] = format(prev['hits'].mean(),'.4f')
		summary['runs/game'] = format(prev['runs'].mean(),'.4f')
		summary['lob/game'] = format(prev['team left on base'].mean(),'.4f')
		summary['errors/game'] = format(prev['errors'].mean(),'.4f')
		summary['avg_margin'] = format(prev['margin'].mean(),'.4f')
		summary['cur_streak'] = prev.iloc[-1]['streak']
		summary['wins/last' + str(prev_games)] = sum(prev['margin'].apply(lambda x: x > 0))
		summary['last game'] = pd.to_datetime(str(prev.iloc[-1]['date']), format='%Y%m%d').date()

	return summary

# normalizes a players name by removing hyphens and apostrophes
# used to ensure the name is recognized by the SDQL database 
def normalize(name):
	normalized = ''
	for char in name:
		if char.isalpha() or char == ' ':
			normalized += char
		elif char == '-':
			normalized += ' '
	return normalized

# dictionary used to convert invalid html characters to their ascii values
special_chars = { ' ' : '%20',
									',' : '%2C',
									':' : '%3A',
									'=' : '%3D',
									'@' : '%40' }

# creates the http query for a batter given the english SDQL query
# replaces all special characters with their ascii equivalent
def batter_query(SDQL):
	url = 'http://api.sportsdatabase.com/mlb/batter_query.json?sdql='
	for char in SDQL:
		if char not in special_chars:
			url += char
		else:
			url += special_chars[char]
	url += '&output=json&api_key=guest'
	return url

# creates the http query for a pitcher given the english SDQL query
# replaces all special characters with their ascii equivalent
def pitcher_query(SDQL):
	url = 'http://api.sportsdatabase.com/mlb/pitcher_query.json?sdql='
	for char in SDQL:
		if char not in special_chars:
			url += char
		else:
			url += special_chars[char]
	url += '&output=json&api_key=guest'
	return url

# creates the http query for a team given the english SDQL query
# replaces all special characters with their ascii equivalent
def team_query(SDQL):
	url = 'http://api.sportsdatabase.com/mlb/query.json?sdql='
	for char in SDQL:
		if char not in special_chars:
			url += char
		else:
			url += special_chars[char]
	url += '&output=json&api_key=guest'
	return url

# converts the date object into an integer
def to_integer(dt_time):
    return 10000*dt_time.year + 100*dt_time.month + dt_time.day

# helper function to run function x number of times
# prevents failed/busy connection from breaking program
def try_x(func,params,x):
	cur = 0
	while cur < x:
		try:
			return True,func(*params)
		except:
			time.sleep(3)
			cur += 1
	return False,'No data available'

#runs the main function using specified paramaters
get_stats(str(cur_date),pitchers_games,batters_games,teams_games)