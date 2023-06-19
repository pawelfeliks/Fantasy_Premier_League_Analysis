import urllib
import urllib.request as ur
import ssl
import base64
from flask import Flask, render_template, request
import seaborn as sns
sns.set_theme()
import matplotlib
matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
sns.set_theme(style='darkgrid')
import sqlite3
import io
import numpy as np
import pandas as pd
pd.set_option('display.max_columns', None)
from matplotlib.ticker import MaxNLocator
import os
import subprocess
import json



ssl._create_default_https_context = ssl._create_unverified_context

# teamID = 620066

app = Flask(__name__)

@app.route('/', methods=['GET'])
def Home():
    return render_template('index.html')


@app.route("/predict", methods=['POST'])
def predict():
    if request.method == 'POST':

        teamID = request.form['teamID']
        print(teamID)
        GameweekRange = int(request.form['GameweekRange'])  # convert to int
        print(GameweekRange)

        # Pobranie generalnych informacji na temat drużyny menadżera FPL

        # base = "https://fantasy.premierleague.com/api/entry/" + str(teamID) + "/"
        # read = urllib2.urlopen(base, timeout=20)

        base = "https://fantasy.premierleague.com/api/entry/" + str(teamID) + "/"
        page = ur.urlopen(base)
        generalTeamData = json.load(page)

        # Pozyskanie szczegółowych informacji odnośnie drużyny trenera w danej kolejce
        gameweekTeamData = {}
        for i in range(1, GameweekRange + 1):
            base = "https://fantasy.premierleague.com/api/entry/" + str(teamID) + "/event/" + str(i) + "/picks/"
            page = ur.urlopen(base)
            data = {"GW" + str(i): json.load(page)}
            gameweekTeamData.update(data)

        # Uzyskanie informacji ogólnych o zespołach PL, zawodnikach oraz szczegółach danych kolejek
        base = "https://fantasy.premierleague.com/api/bootstrap-static/"
        page = ur.urlopen(base)
        generalData = json.load(page)
        elements = generalData["elements"]
        events = generalData["events"]

        # Pobranie imienia oraz nazwiska zawodnika na podstawie ID
        def PlayerName(playerID):
            i = 0
            while i < len(elements):
                if (elements[i]["id"] == playerID):
                    return (elements[i]["first_name"] + " " + elements[i]["second_name"])
                i += 1
            return "ID not found"

        positions = ["GK", "DEF", "MID", "ST"]

        # Pobranie pozycji zawodnika na podstawie ID
        def getPlayerPosition(playerID):
            i = 0
            while i < len(elements):
                if (elements[i]["id"] == playerID):
                    playersElementType = elements[i]["element_type"]
                    playerPosition = positions[playersElementType - 1]
                    return playerPosition
                i += 1
            return "ID not found"

        # Zdobyte punkty przez zawowdników trenera
        def PlayerGwPoints(playerID, gameweek):
            base = "https://fantasy.premierleague.com/api/element-summary/" + str(playerID) + "/"
            page = ur.urlopen(base)
            gwData = json.load(page)
            gwPoints = 0
            for i in range(len(gwData["history"])):
                if gameweek == gwData["history"][i]["round"]:  # aby uwzględnić nieobecność tygodnia gry w json
                    gwPoints = gwPoints + gwData["history"][i]["total_points"]  # w celu uwzględnienia podwójnego gw
            return gwPoints

        # Pobranie szczegółowych danych zespołu w zorganizowanych listach i słownikach
        teamName = generalTeamData["name"]
        points = []
        gameweekRank = []
        overallRank = []
        transfers = []
        transfersCost = []
        benchPoints = []
        teamValue = []
        highestPoints = []
        averagePoints = []
        captain = []
        viceCaptain = []
        captainPoints = []
        viceCaptainPoints = []
        startingTeam = {}
        totalPointsPerLine = {}
        totalPointsPerLineSeason = {"GK": 0, "DEF": 0, "MID": 0, "ST": 0}

        for gw in range(1, GameweekRange + 1):
            # Ogólne dane z każdej kolejki

            points.append(gameweekTeamData["GW" + str(gw)]["entry_history"]["points"])
            gameweekRank.append(gameweekTeamData["GW" + str(gw)]["entry_history"]["rank"])
            overallRank.append(gameweekTeamData["GW" + str(gw)]["entry_history"]["overall_rank"])
            transfers.append(gameweekTeamData["GW" + str(gw)]["entry_history"]["event_transfers"])
            transfersCost.append(gameweekTeamData["GW" + str(gw)]["entry_history"]["event_transfers_cost"])
            benchPoints.append(gameweekTeamData["GW" + str(gw)]["entry_history"]["points_on_bench"])
            teamValue.append(gameweekTeamData["GW" + str(gw)]["entry_history"]["value"])
            highestPoints.append(events[gw - 1]["highest_score"])
            averagePoints.append(events[gw - 1]["average_entry_score"])

            # Dictionary z drużyną startową każdego gw
            startingTeam["GW" + str(gw)] = {}
            for j in range(0, 15):
                if gameweekTeamData["GW" + str(gw)]["picks"][j]["is_captain"] == True:
                    captainPoints.append(PlayerGwPoints(gameweekTeamData["GW" + str(gw)]["picks"][j]["element"], gw))
                    captain.append(PlayerName(gameweekTeamData["GW" + str(gw)]["picks"][j]["element"]))
                elif gameweekTeamData["GW" + str(gw)]["picks"][j]["is_vice_captain"] == True:
                    viceCaptainPoints.append(
                        PlayerGwPoints(gameweekTeamData["GW" + str(gw)]["picks"][j]["element"], gw))
                    viceCaptain.append(PlayerName(gameweekTeamData["GW" + str(gw)]["picks"][j]["element"]))
            for n in range(0, 15):
                startingTeam["GW" + str(gw)]["player" + str(n)] = {}
                startingTeam["GW" + str(gw)]["player" + str(n)]["name"] = PlayerName(
                    gameweekTeamData["GW" + str(gw)]["picks"][n]["element"])
                startingTeam["GW" + str(gw)]["player" + str(n)]["position"] = getPlayerPosition(
                    gameweekTeamData["GW" + str(gw)]["picks"][n]["element"])
                startingTeam["GW" + str(gw)]["player" + str(n)]["points"] = PlayerGwPoints(
                    gameweekTeamData["GW" + str(gw)]["picks"][n]["element"], gw)

            def printStartingTeam(gw):
                for n in range(0, 15):
                    print(startingTeam["GW" + str(gw)]["player" + str(n)]["name"])

            # Dictionary z punktami na wiersz każdy gw
            # range 11 czy 15
            totalPointsPerLine["GW" + str(gw)] = {"GK": 0, "DEF": 0, "MID": 0, "ST": 0}
            for player in range(0, 11):
                if startingTeam["GW" + str(gw)]["player" + str(player)]["position"] == "GK":
                    totalPointsPerLine["GW" + str(gw)]["GK"] = totalPointsPerLine["GW" + str(gw)]["GK"] + \
                                                               startingTeam["GW" + str(gw)]["player" + str(player)][
                                                                   "points"]
                elif startingTeam["GW" + str(gw)]["player" + str(player)]["position"] == "DEF":
                    totalPointsPerLine["GW" + str(gw)]["DEF"] = totalPointsPerLine["GW" + str(gw)]["DEF"] + \
                                                                startingTeam["GW" + str(gw)]["player" + str(player)][
                                                                    "points"]
                elif startingTeam["GW" + str(gw)]["player" + str(player)]["position"] == "MID":
                    totalPointsPerLine["GW" + str(gw)]["MID"] = totalPointsPerLine["GW" + str(gw)]["MID"] + \
                                                                startingTeam["GW" + str(gw)]["player" + str(player)][
                                                                    "points"]
                elif startingTeam["GW" + str(gw)]["player" + str(player)]["position"] == "ST":
                    totalPointsPerLine["GW" + str(gw)]["ST"] = totalPointsPerLine["GW" + str(gw)]["ST"] + \
                                                               startingTeam["GW" + str(gw)]["player" + str(player)][
                                                                   "points"]

            # Dictionary z punktami linię pozycji za cały sezon
            totalPointsPerLineSeason["GK"] = totalPointsPerLineSeason["GK"] + totalPointsPerLine["GW" + str(gw)]["GK"]
            totalPointsPerLineSeason["DEF"] = totalPointsPerLineSeason["DEF"] + totalPointsPerLine["GW" + str(gw)][
                "DEF"]
            totalPointsPerLineSeason["MID"] = totalPointsPerLineSeason["MID"] + totalPointsPerLine["GW" + str(gw)][
                "MID"]
            totalPointsPerLineSeason["ST"] = totalPointsPerLineSeason["ST"] + totalPointsPerLine["GW" + str(gw)]["ST"]

            print("GW" + str(gw) + " : Done.")

        ################################ Wizualizacje ################################
        #import matplotlib.pyplot as plt
        #import numpy as np
        #import matplotlib.ticker as ticker
        #from matplotlib.ticker import MaxNLocator

        gameweek = np.arange(1, GameweekRange + 1)

        fig, ((ax1, ax2), (ax3, ax4), (ax5, ax6), (ax7, ax8)) = plt.subplots(4, 2, figsize=(12, 10))
        fig.suptitle("Team performance : " + teamName, fontsize=15)
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.4, hspace=0.3)
        fig.patch.set_facecolor('lightgrey')

        ### Punkty druyżny
        ax1.plot(gameweek, points, color='green', label='Team FPL points')
        ax1.plot(gameweek, averagePoints, color='red', label='Average FPL points')
        ax1.plot(gameweek, highestPoints, color='blue', label='Highest FPL points')
        ax1.set_xlabel('Gameweek')
        ax1.set_ylabel('FPL points')
        ax1.legend(loc='upper right', frameon=True, prop={'size': 7}, facecolor='lightgrey')
        ax1.xaxis.set_major_locator(MaxNLocator(integer=True))

        ### Ranking zespołu
        gameweekRank = np.array(gameweekRank)
        ax2.bar(gameweek, gameweekRank, color='lightgreen', label='GW Rank', width=0.7)
        ax2.plot(gameweek, overallRank, color='blue', label='Overall rank')
        ax2.set_ylim(ymin=0)
        ax2.set_ylim(ymax=max(gameweekRank + 400000))
        ax2.get_yaxis().get_major_formatter().set_scientific(False)
        ax2.set_xlabel('Gameweek')
        ax2.set_ylabel('Rank')
        ax2.legend(loc='best', frameon=True, prop={'size': 7}, facecolor='lightgrey')
        ax2.xaxis.set_major_locator(MaxNLocator(integer=True))

        rects = ax2.patches
        for rect in rects:
            height = rect.get_height()
            ax2.text(rect.get_x() + rect.get_width() / 2, height + 100000, height, ha='center', va='bottom', size=6)

        ### Wartość drużyny
        ax3.bar(gameweek, list(map(lambda x: x / 10, teamValue)), width=0.6, color='lightgreen')
        ax3.set_ylim(ymin=min(list(map(lambda x: x / 10, teamValue))) - 0.5)
        ax3.set_ylim(ymax=max(list(map(lambda x: x / 10, teamValue))) + 0.5)
        ax3.set_xlabel('Gameweek')
        ax3.set_ylabel('Team Value (incl. bank)')
        ax3.xaxis.set_major_locator(MaxNLocator(integer=True))
        rects = ax3.patches
        labels = [sum(x) for x in zip(list(map(lambda x: round(x / 10, 1), teamValue)))]
        for rect, label in zip(rects, labels):
            height = rect.get_height()
            ax3.text(rect.get_x() + rect.get_width() / 2, height + 0.1, label, ha='center', va='bottom', size=6)

        ### Transfery klubowe
        ax44 = ax4.twinx()
        ax4.bar(gameweek, transfers, color='lightgreen', label='Number of transfers', width=0.7)
        ax44.plot(gameweek, transfersCost, color='red', label='Transfers cost')
        ax4.set_xlabel('Gameweek')
        ax4.set_ylabel('Number of transfers')
        ax44.set_ylabel('Transfers cost')
        ax4.legend(loc=2, frameon=True, prop={'size': 7}, facecolor='lightgrey')
        ax44.legend(loc=1, frameon=True, prop={'size': 7}, facecolor='lightgrey')
        ax44.set_ylim(ymin=0)
        ax44.set_ylim(ymax=max(transfersCost) + 1)
        ax4.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax44.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax4.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax44.xaxis.set_major_locator(MaxNLocator(integer=True))

        ### Punkty kapitana i vice-kapitana
        captainPoints = np.array(captainPoints)
        captainDisplay = []

        for n in range(GameweekRange):
            captainDisplay.append(str(n + 1) + " - " + str(captain[n]))  # convert to str
        mask1 = captainPoints > 3
        mask2 = captainPoints <= 3

        ax5.bar(gameweek[mask1], list(map(lambda x: x * 2, captainPoints[mask1])), width=0.7, color='green',
                label='Captain points > 3')
        ax5.bar(gameweek[mask2], list(map(lambda x: x * 2, captainPoints[mask2])), width=0.7, color='lightgreen',
                label='Captain points <= 3')
        ax5.set_ylim(ymin=0)
        ax5.set_ylim(ymax=max(list(map(lambda x: x * 2, captainPoints))) + 5)
        ax5.set_xticks(gameweek)
        ax5.set_xticklabels(captainDisplay, rotation=7, ha="right", size=6)
        ax5.set_ylabel('Captain FPL points')
        ax5.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax5.legend(loc=2, frameon=True, prop={'size': 7}, facecolor='lightgrey')
        rects = ax5.patches
        for rect in rects:
            height = rect.get_height()
            ax5.text(rect.get_x() + rect.get_width() / 2, height + 0.6, height, ha='center', va='bottom', size=6)

        ### Punkty vice kapitana
        viceCaptainPoints = np.array(viceCaptainPoints)
        viceCaptainDisplay = []
        for n in range(0, GameweekRange):
            viceCaptainDisplay.append(str(n + 1) + " - " + viceCaptain[n])
        mask1 = viceCaptainPoints > 3
        mask2 = viceCaptainPoints <= 3
        ax7.bar(gameweek[mask1], list(map(lambda x: x * 2, viceCaptainPoints[mask1])), width=0.5, color='blue',
                label='Vice- Captain points > 3')
        ax7.bar(gameweek[mask2], list(map(lambda x: x * 2, viceCaptainPoints[mask2])), width=0.5, color='lightblue',
                label='Vice-Captain points <= 3')
        ax7.set_ylim(ymin=0)
        ax7.set_ylim(ymax=max(list(map(lambda x: x * 2, viceCaptainPoints))) + 5)
        ax7.set_xticks(gameweek)
        ax7.set_xticklabels(viceCaptainDisplay, rotation=7, ha="right", size=5)
        ax7.set_ylabel('Vice Captain FPL points')
        ax7.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax7.legend(loc=2, frameon=True, prop={'size': 7}, facecolor='lightgrey')
        rects = ax7.patches
        for rect in rects:
            height = rect.get_height()
            ax7.text(rect.get_x() + rect.get_width() / 2, height + 0.5, height, ha='center', va='bottom', size=5)

        ## Punkty na ławce
        ax88 = ax8.twinx()
        ax8.bar(gameweek, benchPoints, color='yellow', label='Number of points', width=0.7)
        ax8.set_xlabel('Gameweek')
        ax8.set_ylabel('Bench players points')
        ax8.legend(loc=2, frameon=True, prop={'size': 7}, facecolor='lightgrey')
        ax8.legend(loc=1, frameon=True, prop={'size': 7}, facecolor='lightgrey')
        ax8.set_ylim(ymin=0)
        ax8.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax8.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax8.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax8.xaxis.set_major_locator(MaxNLocator(integer=True))

        ### Punkty konkretnej pozycji
        positions = list(totalPointsPerLineSeason.keys())
        pointsPos = list(totalPointsPerLineSeason.values())
        colors = ['lightblue', 'lightyellow', 'lightgreen', 'tomato']

        def func(pct, allvals):
            absolute = int(pct / 100. * np.sum(allvals))
            return "{:.1f}%\n({:d} pts)".format(pct, absolute)

        wedges, texts, autotexts = ax6.pie(pointsPos, autopct='%1.0f%%',
                                           textprops={'fontsize': 7}, colors=colors, radius=1.2,
                                           explode=[0.1, 0.1, 0.1, 0.1], shadow=True)

        ax6.legend(wedges, positions,
                   title="Positions",
                   loc="center right",
                   bbox_to_anchor=(1.5, 0.1, 0.5, 1),
                   facecolor='lightgrey')

        ax6.set_xlabel("Points per position over the season")

        fig.tight_layout(rect=[0, 0.03, 1, 0.95])  # dopasowuje wykresy do wielkosci okna wyswieltania
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)  # robi przerwe miedzy tytulem a wykresami

        print('the end')

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_data = urllib.parse.quote(base64.b64encode(img.read()).decode())

        # plotly.offline.plot(img, filename = 'results.html', auto_open=False)

        return render_template('results.html', plot_url=plot_data)


if __name__ == "__main__":
    app.run(debug=True)


# Źródło danych
base = "https://fantasy.premierleague.com/api/bootstrap-static/"
PATH = '/Users/wiktorniewiadomski/Documents/GitHub/pythonProject6/Fantasy-Premier-League/data/2022-23/'

# Zautomatyzowane aktualizowanie danych z gita
os.chdir(PATH)
subprocess.run(["git", "pull"])

# Create a default SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Use the SSL context to open the URL
page = ur.urlopen(base, context=ssl_context)

# Stworzenie dodatkowego wykresu na podstawie danych z understat
elements_df = pd.read_csv(PATH + 'players_raw.csv')
teams_df = pd.read_csv(PATH + 'teams.csv')
understat_player_df = pd.read_csv(PATH + 'understat/understat_player.csv')
generalData = json.load(page)
element_types = generalData["element_types"]
elements = generalData["elements"]
events = generalData["events"]

# Stworzenie ramek danych z ważnymi informacjami odnośnie zawodników, ich pozycji oraz zespołów
element_types_df = pd.DataFrame(element_types)

# Wyselekcjonowanie jedynie kluczowych kolumn z parametru elements
main_df = elements_df[
    ['web_name', 'first_name', 'team', 'element_type', 'now_cost', 'selected_by_percent', 'transfers_in',
     'transfers_out', 'form', 'event_points', 'total_points', 'bonus', 'points_per_game', 'value_season',
     'minutes', 'goals_scored', 'assists', 'ict_index', 'clean_sheets', 'saves', 'expected_goals',
     'expected_assists', 'expected_goal_involvements', 'expected_goal_involvements_per_90',
     'expected_goals_conceded', 'ep_this', 'ep_next']]

# Stworzenie nowego słownika w celu uwzględnienia realnej liczby gier drużyn
games_played = [['Arsenal', '36'], ['Aston Villa', '36'], ['Bournemouth', '36'], ['Brentford', '36'],
                ['Brighton', '35'], ['Chelsea', '35'], ['Crystal Palace', '36'], ['Everton', '36'],
                ['Fulham', '36'], ['Leicester', '36'], ['Leeds', '36'], ['Liverpool', '36'], ['Man City', '35'],
                ['Man Utd', '35'], ['Newcastle', '36'], ["Nott'm Forest", '36'], ['Southampton', '36'],
                ['Spurs', '36'], ['West Ham', '36'], ['Wolves', '36']]

# Przekształcenie w ramkę danych
played_df = pd.DataFrame(games_played, columns=['team', 'games_played'])

# Zastąpienie pierwotnej kolumny z ramki danych
teams_df['played'] = played_df['games_played'].astype(str).astype(int)

# Dodanie kolumn z teams_df do ramki main_df
main_df = pd.merge(left=main_df,
                   right=teams_df[['id', 'name', 'played', 'strength_overall_away', 'strength_overall_home']],
                   left_on='team', right_on='id', how='left')

# Usunięcie redundatnych kolumn z ramki main_df
main_df = main_df.drop(["id", "team"], axis=1)

# Zmiana nazwy kolumny na bardziej intuicyjną
main_df = main_df.rename(columns={'name': 'team'})

# Dodanie kolumn z elements_types_df do ramki main_df
main_df = pd.merge(left=main_df, right=element_types_df[['id', 'singular_name']], left_on='element_type',
                   right_on='id', how='left')

# Usunięcie redundatnych kolumn z ramki main_df
main_df = main_df.drop(["id", "element_type"], axis=1)

# Zmiana nazwy kolumny na bardziej intuicyjną
main_df = main_df.rename(columns={'singular_name': 'position'})

# Profilaktyczne konwertowanie kolumn, aby uniknąć potencjalnych problemów w trakcie obliczeń
main_df['expected_goals'] = main_df.expected_goals.astype(float)
main_df['expected_assists'] = main_df.expected_assists.astype(float)
main_df['minutes'] = main_df.minutes.astype(float)
main_df['value'] = main_df.value_season.astype(float)
main_df['ict_score'] = main_df.ict_index.astype(float)
main_df['current_form'] = main_df.form.astype(float)
main_df['selection_percentage'] = main_df.selected_by_percent.astype(float)
main_df['ep_this'] = main_df.ep_next.astype(float)
main_df['ep_next'] = main_df.ep_next.astype(float)

# Dodanie kolumny udziału bramkowego = bramki + asysty
main_df['total_contribution'] = main_df['goals_scored'] + main_df['assists']

# Dodanie kolumny przewidującej zdobyte punkty w 2 najbliższych kolejkach
main_df['xPoints'] = (main_df['ep_this'] + main_df['ep_next']) / 2

# pozbywamy się zawodników, którzy nie grają
main_df = main_df[main_df['minutes'] > 0]

# Tworzenie połączenia do bazy danych SQLite
conn = sqlite3.connect('mydatabase.db')

# Zapisywanie ramki danych do bazy danych jako tabeli o nazwie 'main_table'
main_df.to_sql('main_table', conn, if_exists='replace')

# Wykonanie zapytania SQL na bazie danych
#query = "SELECT * FROM main_table where position = 'Goalkeeper'"
#result = pd.read_sql_query(query, conn)

# Wyświetlenie najciekawszych wyników zapytania
query = "SELECT web_name, total_points FROM main_table ORDER BY total_points DESC LIMIT 10"
ex1 = pd.read_sql_query(query, conn)

query = "SELECT web_name, now_cost, total_points FROM main_table WHERE now_cost < 5.0 AND total_points > 50"
ex2 = pd.read_sql_query(query, conn)

query = "SELECT web_name, MAX(selected_by_percent) as max_selected FROM main_table GROUP BY team"
ex3 = pd.read_sql_query(query, conn)

query = "SELECT web_name, minutes FROM main_table ORDER BY minutes DESC LIMIT 5"
ex4 = pd.read_sql_query(query, conn)

query = "SELECT web_name, goals_scored FROM main_table ORDER BY goals_scored DESC"
ex5 = pd.read_sql_query(query, conn)

query = "SELECT * FROM main_table"
ex6 = pd.read_sql_query(query, conn)

#query = "WITH top_players AS (SELECT printf('%s %s (%s)', first_name, web_name, position) AS NAME, total_points, minutes, now_cost AS price FROM main_table ORDER BY CAST(total_points AS INTEGER) DESC LIMIT 15) SELECT NAME, total_points, now_cost, minutes, CAST(total_points AS FLOAT) / CAST(now_cost AS FLOAT) AS roi, CAST(total_points AS FLOAT) / CAST(minutes AS FLOAT) AS rom, CAST(total_points AS FLOAT) / CAST(now_cost AS FLOAT) + CAST(total_points AS FLOAT) / CAST(minutes AS FLOAT) AS rostar FROM top_players"
#ex7 = pd.read_sql_query(query, conn)

# Punkty/cena i total_points w ujęciu na pozycje zawodników grających
points_pos = np.round(
    main_df.groupby('position', as_index=False).aggregate({'value': np.mean, 'total_points': np.sum}), 2)
points_pos.sort_values('value', ascending=False)

# Punkty/cena i total_points w ujęciu na drużyny
teams_pos = np.round(
    main_df.groupby('team', as_index=False).aggregate({'value': np.mean, 'total_points': np.sum}), 2)
teams_pos_df = teams_pos.sort_values('value', ascending=False)
teams_pos_df['games_played'] = teams_df['played']

# średnia wartość 3 najlepszych zawodników każdej drużyny pod kątem xGi
top3p_xgi = main_df.sort_values('expected_goal_involvements', ascending=False).groupby('team',
                                                                                       as_index=False).head(3)
top3t_xgi = np.round(
    top3p_xgi.groupby('team', as_index=False).aggregate({'expected_goal_involvements': np.mean}), 1)

# xGc wszystkich zespołów
p_egc = main_df.sort_values('expected_goals_conceded', ascending=False).groupby('team', as_index=False).head(1)
p_egc['minutes_per_expected_goals_conceded'] = p_egc['minutes'] / p_egc['expected_goals_conceded']
t_egc = np.round(
    p_egc.groupby('team', as_index=False).aggregate({'minutes_per_expected_goals_conceded': np.mean}), 1)

# Pogrupowanie danych ze względu na value i total_points oraz dodanie 3 kolumn
teams_pos = np.round(
    main_df.groupby('team', as_index=False).aggregate({'value': np.mean, 'total_points': np.sum}), 2)
teams_pos_df = teams_pos
teams_pos_df['games_played'] = teams_df['played']
teams_pos_df['value_per_game'] = np.round(teams_pos_df['value'] / teams_df['played'], 2)
teams_pos_df['points_per_game'] = np.round(teams_pos_df['total_points'] / teams_df['played'], 2)
teams_pos_df['minutes_per_expected_goals_conceded'] = t_egc['minutes_per_expected_goals_conceded']
teams_pos_df['expected_goal_involvements_by_top_3_players'] = top3t_xgi['expected_goal_involvements']

# Wizualiacja wyników
fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(20, 7))
plt.subplots_adjust(hspace=0.25, wspace=0.25)
fig.suptitle("Teams", fontsize=15)
teams_pos_df.sort_values('expected_goal_involvements_by_top_3_players').plot.barh(ax=axes[0, 0], x="team",
                                                                                  y="expected_goal_involvements_by_top_3_players",
                                                                                  subplots=True,
                                                                                  color='#0087F1')
teams_pos_df.sort_values('value_per_game').plot.barh(ax=axes[0, 1], x="team", y="value_per_game", subplots=True,
                                                     color='#2BBD00')
teams_pos_df.sort_values('minutes_per_expected_goals_conceded').plot.barh(ax=axes[1, 0], x="team",
                                                                          y="minutes_per_expected_goals_conceded",
                                                                          subplots=True, color="#EB2000")
teams_pos_df.sort_values('points_per_game').plot.barh(ax=axes[1, 1], x="team", y="points_per_game",
                                                      subplots=True, color="#FF8000")

# Przypisanie do zmiennych zawodników konkretnych formacji
query = "SELECT * FROM main_table where position = 'Goalkeeper'"
result = pd.read_sql_query(query, conn)
gk_df = result[
    ['web_name', 'team', 'selection_percentage', 'now_cost', 'clean_sheets', 'saves', 'bonus', 'total_points',
     'value', 'current_form', 'transfers_in', 'xPoints']]
def_df = main_df.loc[main_df.position == 'Defender']
def_df = def_df[
    ['web_name', 'team', 'selection_percentage', 'now_cost', 'clean_sheets', 'assists', 'goals_scored',
     'total_contribution', 'ict_score', 'bonus', 'total_points', 'value', 'expected_goals', 'expected_assists',
     'expected_goal_involvements', 'expected_goals_conceded', 'current_form', 'xPoints']]
mid_df = main_df.loc[main_df.position == 'Midfielder']
mid_df = mid_df[
    ['web_name', 'team', 'selection_percentage', 'now_cost', 'assists', 'goals_scored', 'total_contribution',
     'ict_score', 'current_form', 'bonus', 'total_points', 'value', 'expected_goals', 'expected_assists',
     'expected_goal_involvements', 'expected_goals_conceded', 'xPoints']]
fwd_df = main_df.loc[main_df.position == 'Forward']
fwd_df = fwd_df[
    ['web_name', 'team', 'selection_percentage', 'now_cost', 'assists', 'goals_scored', 'total_contribution',
     'ict_score', 'current_form', 'minutes', 'bonus', 'total_points', 'value', 'expected_goals',
     'expected_assists', 'expected_goal_involvements', 'expected_goals_conceded', 'xPoints']]

def plot_scatter(ax, x, y, title, df):
    df.plot.scatter(x=x, y=y, s=50, alpha=.5, ax=ax, figsize=(15, 9), title=title)
    for i, txt in enumerate(df.web_name):
        now_cost = df.now_cost.iat[i] / 10
        ax.annotate(f'{txt},£{now_cost}', (df[x].iat[i], df[y].iat[i]), ha='center', xytext=(0, 5),
                    textcoords='offset points')
    ax.grid(which='both', axis='both', ls='-')

# Wizualizcja wyników dla bramkarzy
query = "SELECT * FROM main_table where position = 'Goalkeeper' and value > 20"
topgk_df = pd.read_sql_query(query, conn)

fig, axes = plt.subplots(2, 2, figsize=(30, 20))
fig.suptitle("Goalkeepers", fontsize=15)
fig.subplots_adjust(left=0.05, bottom=0.06, right=0.97, top=0.88, wspace=0.13, hspace=0.25)
fig.patch.set_facecolor('#DFED51')

plot_scatter(axes[0, 0], 'total_points', 'now_cost', "goalkeepers: total_points v cost", topgk_df)
plot_scatter(axes[0, 1], 'total_points', 'saves', "goalkeepers: total_points v saves", topgk_df)
plot_scatter(axes[1, 0], 'total_points', 'clean_sheets', "goalkeepers: total_points v clean_sheets", topgk_df)
plot_scatter(axes[1, 1], 'selection_percentage', 'current_form',
             "goalkeepers: selection_percentage v current_form", topgk_df)

plt.tight_layout()

# Sortowanie obrońców po ilości zdobytych punktów
def_df.sort_values('total_points', ascending=False).head(5)

# Utworzenie zmiennej jedynie dla topowych obrońców
topdef_df = def_df = def_df[def_df['value'] > 21]

# Utworzenie zmiennej jedynie dla pechowych obrońców
unluckydef_df = def_df.loc[def_df.ict_score > 115]
unluckydef_df.sort_values('ict_score', ascending=False).head(10)

# Wizualizcja wyników dla obrońców

fig, axes = plt.subplots(2, 2, figsize=(30, 20))
fig.suptitle("Defenders", fontsize=15)
fig.subplots_adjust(left=0.05, bottom=0.06, right=0.97, top=0.88, wspace=0.13, hspace=0.25)
fig.patch.set_facecolor('#FF4617')

plot_scatter(axes[0, 0], 'total_points', 'now_cost', "defenders: total_points v cost", topdef_df)
plot_scatter(axes[0, 1], 'total_points', 'ict_score', "defenders: total_points v ict_score", unluckydef_df)
plot_scatter(axes[1, 0], 'expected_goal_involvements', 'clean_sheets',
             "defenders: expected_goal_involvements v clean_sheets", topdef_df)
plot_scatter(axes[1, 1], 'selection_percentage', 'current_form',
             "defenders: selection_percentage v current_form", topdef_df)

plt.tight_layout()

# Utworzenie zmiennej jedynie dla topowych pomocników
topmid_df = mid_df.loc[mid_df.ict_score > 200]

# Wizualizcja wyników dla pomocników

fig, axes = plt.subplots(2, 2, figsize=(30, 20))
fig.suptitle("Midfielders", fontsize=15)
fig.subplots_adjust(left=0.05, bottom=0.06, right=0.97, top=0.88, wspace=0.13, hspace=0.25)
fig.patch.set_facecolor('#66F26F')

plot_scatter(axes[0, 0], 'total_points', 'now_cost', "midfielders: total_points v cost", topmid_df)
plot_scatter(axes[0, 1], 'total_points', 'ict_score', "midfielders: total_points v ict_score", topmid_df)
plot_scatter(axes[1, 0], 'expected_goal_involvements', 'total_contribution',
             "midfielders: expected_goal_involvements v total_contribution", topmid_df)
plot_scatter(axes[1, 1], 'selection_percentage', 'current_form',
             "midfielders: selection_percentage v current_form", topmid_df)

plt.tight_layout()

# Utworzenie zmiennej jedynie dla topowych napastników
topfwd_df = fwd_df.loc[fwd_df.ict_score > 130]

# Wizualizcja wyników dla napastników

fig, axes = plt.subplots(2, 2, figsize=(30, 20))
fig.suptitle("Forwards", fontsize=15)
fig.subplots_adjust(left=0.05, bottom=0.06, right=0.97, top=0.88, wspace=0.13, hspace=0.25)
fig.patch.set_facecolor('#78E1FF')

plot_scatter(axes[0, 0], 'total_points', 'now_cost', "forwards: total_points v cost", topfwd_df)
plot_scatter(axes[0, 1], 'total_points', 'ict_score', "forwards: total_points v ict_score", topfwd_df)
plot_scatter(axes[1, 0], 'expected_goal_involvements', 'total_contribution',
             "forwards: expected_goal_involvements v total_contribution", topfwd_df)
plot_scatter(axes[1, 1], 'selection_percentage', 'current_form',
             "forwards: selection_percentage v current_form", topfwd_df)

plt.tight_layout()

# Wyselekcjonowanie top 3 zawodników z każdej pozycji na podstawie value
top5value_gk_df = gk_df.nlargest(3, 'value')
top5value_def_df = def_df.nlargest(3, 'value')
top5value_mid_df = mid_df.nlargest(3, 'value')
top5value_fwd_df = fwd_df.nlargest(3, 'value')

# Wyselekcjonowanie top 3 zawodników z każdej pozycji na podstawie value_form
top5inform_gk_df = gk_df.nlargest(3, 'current_form')
top5inform_def_df = def_df.nlargest(3, 'current_form')
top5inform_mid_df = mid_df.nlargest(3, 'current_form')
top5inform_fwd_df = fwd_df.nlargest(3, 'current_form')

# Wyselekcjonowanie top 3 zawodników z każdej pozycji na podstawie xPoints
top5xp_gk_df = gk_df.nlargest(3, 'xPoints')
top5xp_def_df = def_df.nlargest(3, 'xPoints')
top5xp_mid_df = mid_df.nlargest(3, 'xPoints')
top5xp_fwd_df = fwd_df.nlargest(3, 'xPoints')

# Wyselekcjonowanie top 3 zawodników z każdej pozycji na podstawie xGChain i xGBuildup
top10xGC = understat_player_df.nlargest(5, 'xGChain')
top10xGB = understat_player_df.nlargest(5, 'xGBuildup')

# Wizualizcja wyników dla top 3 zawodników z każdej pozycji
fig, axes = plt.subplots(2, 2, figsize=(30, 20))
fig.suptitle("All Players", fontsize=15)
fig.subplots_adjust(left=0.05, bottom=0.06, right=0.97, top=0.88, wspace=0.13, hspace=0.25)
fig.patch.set_facecolor('#D8FFFF')

ax = axes[0, 0]
top5value_gk_df.plot.scatter(x='value', y='total_points', color='#DFED51', label='GK', s=50, alpha=.5, ax=ax,
                             figsize=(15, 9), title="Top 3 xPoints Players by Position")
for i, txt in enumerate(top5value_gk_df.web_name):
    now_cost = top5value_gk_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5value_gk_df.value.iat[i], top5value_gk_df.total_points.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5value_def_df.plot.scatter(x='value', y='total_points', color='#FF4617', label='DEF', s=50, ax=ax)
for i, txt in enumerate(top5value_def_df.web_name):
    now_cost = top5value_def_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5value_def_df.value.iat[i], top5value_def_df.total_points.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5value_mid_df.plot.scatter(x='value', y='total_points', color='#66F26F', label='MID', s=50, ax=ax)
for i, txt in enumerate(top5value_mid_df.web_name):
    now_cost = top5value_mid_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5value_mid_df.value.iat[i], top5value_mid_df.total_points.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5value_fwd_df.plot.scatter(x='value', y='total_points', color='#78E1FF', label='FWD', s=50, ax=ax)
for i, txt in enumerate(top5value_fwd_df.web_name):
    now_cost = top5value_fwd_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5value_fwd_df.value.iat[i], top5value_fwd_df.total_points.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
ax.legend(loc='best', frameon=True, prop={'size': 7}, facecolor='lightgrey')
ax.xaxis.set_major_locator(MaxNLocator(integer=True))

ax = axes[0, 1]
top5inform_gk_df.plot.scatter(x='selection_percentage', y='current_form', color='#DFED51', label='GK', s=50,
                              alpha=.5, ax=ax, title="Top 3 inform Players by Position")
for i, txt in enumerate(top5inform_gk_df.web_name):
    now_cost = top5inform_gk_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}',
                (top5inform_gk_df.selection_percentage.iat[i], top5inform_gk_df.current_form.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5inform_def_df.plot.scatter(x='selection_percentage', y='current_form', color='#FF4617', label='DEF', s=50,
                               ax=ax)
for i, txt in enumerate(top5inform_def_df.web_name):
    now_cost = top5inform_def_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}',
                (top5inform_def_df.selection_percentage.iat[i], top5inform_def_df.current_form.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5inform_mid_df.plot.scatter(x='selection_percentage', y='current_form', color='#66F26F', label='MID', s=50,
                               ax=ax)
for i, txt in enumerate(top5inform_mid_df.web_name):
    now_cost = top5inform_mid_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}',
                (top5inform_mid_df.selection_percentage.iat[i], top5inform_mid_df.current_form.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5inform_fwd_df.plot.scatter(x='selection_percentage', y='current_form', color='#78E1FF', label='FWD', s=50,
                               ax=ax)
for i, txt in enumerate(top5inform_fwd_df.web_name):
    now_cost = top5inform_fwd_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}',
                (top5inform_fwd_df.selection_percentage.iat[i], top5inform_fwd_df.current_form.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
ax.legend(loc='best', frameon=True, prop={'size': 7}, facecolor='lightgrey')
ax.xaxis.set_major_locator(MaxNLocator(integer=True))

ax = axes[1, 0]
top5xp_gk_df.plot.scatter(x='selection_percentage', y='xPoints', color='#DFED51', label='GK', s=50, alpha=.5,
                          ax=ax, title="Top 3 Players by Position for next gws")
for i, txt in enumerate(top5xp_gk_df.web_name):
    now_cost = top5xp_gk_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5xp_gk_df.selection_percentage.iat[i], top5xp_gk_df.xPoints.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5xp_def_df.plot.scatter(x='selection_percentage', y='xPoints', color='#FF4617', label='DEF', s=50, ax=ax)
for i, txt in enumerate(top5xp_def_df.web_name):
    now_cost = top5xp_def_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5xp_def_df.selection_percentage.iat[i], top5xp_def_df.xPoints.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5xp_mid_df.plot.scatter(x='selection_percentage', y='xPoints', color='#66F26F', label='MID', s=50, ax=ax)
for i, txt in enumerate(top5xp_mid_df.web_name):
    now_cost = top5xp_mid_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5xp_mid_df.selection_percentage.iat[i], top5xp_mid_df.xPoints.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
top5xp_fwd_df.plot.scatter(x='selection_percentage', y='xPoints', color='#78E1FF', label='FWD', s=50, ax=ax)
for i, txt in enumerate(top5xp_fwd_df.web_name):
    now_cost = top5xp_fwd_df.now_cost.iat[i] / 10
    ax.annotate(f'{txt},£{now_cost}', (top5xp_fwd_df.selection_percentage.iat[i], top5xp_fwd_df.xPoints.iat[i]),
                ha='center', xytext=(0, 5), textcoords='offset points')
ax.legend(loc='best', frameon=True, prop={'size': 7}, facecolor='lightgrey')
ax.xaxis.set_major_locator(MaxNLocator(integer=True))

ax = axes[1, 1]
top10xGC.plot.scatter(x='xGChain', y='xGBuildup', color='Green', s=50, label='xGChain', alpha=.5, ax=ax,
                      title="Top 5 xGChain and xGBuildup Players")
for i, txt in enumerate(top10xGC.player_name):
    ax.annotate(txt, (top10xGC.xGChain.iat[i], top10xGC.xGBuildup.iat[i]), ha='center', xytext=(0, 5),
                textcoords='offset points')
top10xGB.plot.scatter(x='xGChain', y='xGBuildup', color='Blue', s=50, ax=ax, label='xGBuildup')
for i, txt in enumerate(top10xGB.player_name):
    ax.annotate(txt, (top10xGB.xGChain.iat[i], top10xGB.xGBuildup.iat[i]), ha='center', xytext=(0, 5),
                textcoords='offset points')
ax.legend(loc='best', frameon=True, prop={'size': 7}, facecolor='lightgrey')
ax.xaxis.set_major_locator(MaxNLocator(integer=True))

plt.show()

