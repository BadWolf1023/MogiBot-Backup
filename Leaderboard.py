'''
Created on Nov 5, 2020

@author: willg
'''
from builtins import isinstance
from _datetime import datetime

'''
Created on Sep 28, 2020

@author: willg
'''
import discord
import Shared
from datetime import datetime, timedelta
import asyncio
from typing import List
import dill as p

medium_delete = 10
long_delete = 30

in_testing_data_mode = False

lounge_player_data_rt = None
lounge_player_data_ct = None
global_cached = {}
rt_main_url = "https://mariokartboards.com/lounge/json/player.php?type=rt&all"
ct_main_url = "https://mariokartboards.com/lounge/json/player.php?type=ct&all"
rt_specific_url = "https://mariokartboards.com/lounge/json/player.php?type=rt&name="
ct_specific_url = "https://mariokartboards.com/lounge/json/player.php?type=ct&name="
currently_pulling = True
interval_time = 10 #wait this many seconds between each ping to mkboards.com
extra_wait_time = 20
chunk_size = 25
time_between_pulls = timedelta(hours=3)
rt_last_updated = None
ct_last_updated = None
rt_progress = 0.0
ct_progress = 0.0

date_filter_time = timedelta(days=14)
TOP_N_RESULTS = 10

LEADERBOARD_WAIT_TIME = timedelta(seconds=20)



leaderboard_terms = {"leader", "leaderboard"}
leaderboard_type_terms = {'rt', 'ct'}
#key is command arg, tuple is:
#field name in the JSON, embed name, time filter, and reversed, minimum events needed
stat_terms = {'avg10':('average10_score', "Highest Average (Last 10)", True, True, 5),
              'topscore':('top_score', 'Top Score', False, True, -1),
              'mmr':('current_mmr', "Current MMR", False, True, 5),
              'mmrgain10':('gainloss10_mmr', "Most MMR Gained (Last 10)", True, True, -1),
              'mmrloss10':('gainloss10_mmr', "Most MMR Lost (Last 10)", True, False, -1),
              'pens':('penalties', "Most Penalties", False, False, -1),
              'peakmmr':('peak_mmr', "Peak MMR", False, True, 5),
              'wins':('wins', "Most Wins", False, True, -1),
              'losses':('loss', "Most Losses", False, True, -1),
              'maxgain':('max_gain_mmr', "Largest MMR Gain", False, True, -1),
              'maxloss':('max_loss_mmr', "Largest MMR Loss", False, False, -1),
              'winpercentage':('win_percentage', "Win Percentage", True, True, 10),
              'wins10':('wins10', "Most Wins (Last 10)", True, True, -1),
              'losses10':('loss10', "Most Losses (Last 10)", True, True, -1),
              'winstreak':('win_streak', "Current Win Streak", True, True, -1),
              'avg':('average_score', "Highest Average", False, True, 10),
              'events':('total_wars', "Most Events Played", False, True, -1)
              }
mult_100_fields = {"win_percentage"}

def fix_datas():
    for p in lounge_player_data_rt:
        if isinstance(lounge_player_data_rt[p]['update_date'], str):
            try:
                lounge_player_data_rt[p]['update_date'] = datetime.strptime(lounge_player_data_rt[p]['update_date'], '%Y-%m-%d %H:%M:%S')
            except:
                print(lounge_player_data_rt[p]['update_date'])
                lounge_player_data_rt[p]['update_date'] = datetime.min
                
    for p in lounge_player_data_ct:
        if isinstance(lounge_player_data_ct[p]['update_date'], str):
            try:
                lounge_player_data_ct[p]['update_date'] = datetime.strptime(lounge_player_data_ct[p]['update_date'], '%Y-%m-%d %H:%M:%S')
            except:
                print(lounge_player_data_ct[p]['update_date'])
                lounge_player_data_ct[p]['update_date'] = datetime.min
                
def all_player_is_corrupt(json_data):
    if not isinstance(json_data, list):
        return True
    if len(json_data) < 1:
        return True
    
    for item in json_data:
        if not isinstance(item, dict):
            return True
        if 'pid' not in item or 'name' not in item or not isinstance(item['pid'], int) or not isinstance(item['name'], str):
            return True
    return False

def detailed_players_is_corrupt(json_data):
    if not isinstance(json_data, list):
        return True
    #update_date":"2020-11-02 23:41:22"
    for player in json_data:
        
        if not isinstance(player, dict):
            return True
         
        if 'pid' in player and isinstance(player['pid'], int) \
        and 'name' in player and isinstance(player['name'], str) \
        and 'strikes' in player and isinstance(player['strikes'], int) \
        and 'current_mmr' in player and isinstance(player['current_mmr'], int) \
        and 'peak_mmr' in player and isinstance(player['peak_mmr'], int) \
        and 'lowest_mmr' in player and isinstance(player['lowest_mmr'], int) \
        and 'wins' in player and isinstance(player['wins'], int) \
        and 'loss' in player and isinstance(player['loss'], int) \
        and 'max_gain_mmr' in player and isinstance(player['max_gain_mmr'], int) \
        and 'max_loss_mmr' in player and isinstance(player['max_loss_mmr'], int) \
        and 'win_percentage' in player and isinstance(player['win_percentage'], (float, int)) \
        and 'gainloss10_mmr' in player and isinstance(player['gainloss10_mmr'], int) \
        and 'wins10' in player and isinstance(player['wins10'], int) \
        and 'loss10' in player and isinstance(player['loss10'], int) \
        and 'win10_percentage' in player and isinstance(player['win10_percentage'], (float, int)) \
        and 'win_streak' in player and isinstance(player['win_streak'], int) \
        and 'top_score' in player and isinstance(player['top_score'], int) \
        and 'average_score' in player and isinstance(player['average_score'], (float, int)) \
        and 'average10_score' in player and isinstance(player['average10_score'], (float, int)) \
        and 'total_wars' in player and isinstance(player['total_wars'], int) \
        and 'penalties' in player and isinstance(player['penalties'], int) \
        and 'total_strikes' in player and isinstance(player['total_strikes'], int) \
        and 'ranking' in player and isinstance(player['ranking'], str) and (player['ranking'].isnumeric() or player['ranking'] == "Unranked") \
        and 'update_date' in player and isinstance(player['update_date'], str) \
        and 'url' in player and isinstance(player['url'], str):
            continue
        
        for key in player:
            print('key:', key, 'value:', player[key], "type:", type(player[key]))
        return True
    return False


async def pull_chunk(player_name:List[str], new_full_data_dict, is_rt=True):
    await asyncio.sleep(interval_time)
    success = True
    specific_url = rt_specific_url if is_rt else ct_specific_url
    specific_url += ",".join(player_name).replace(" ","")
    chunk_data = None
    for i in range(5):
        try:
            chunk_data = await Shared.fetch(specific_url)
            chunk_is_corrupt = detailed_players_is_corrupt(chunk_data)
            if chunk_is_corrupt:
                print("Chunk was corrupt")
            else:
                break
        except:
            print("Failed to send url request, attempt #" + str(i))
        if i < 4:
            await asyncio.sleep(interval_time*(i+1)) #We wait an increasing amount of time if we fail, we try 5 times remember
    else: #not breaking the loop means we failed 5 times
        success = False
    
    if success and chunk_data != None:
        for player in chunk_data:
            if player['ranking'] == 'Unranked':
                continue
            try:
                if isinstance(player['update_date'], str):
                    player['update_date'] = datetime.strptime(player['update_date'], '%Y-%m-%d %H:%M:%S')
                else:
                    player['update_date'] = datetime.min
            except:
                print(player['update_date'])
                player['update_date'] = datetime.min
            new_full_data_dict[player['pid']] = player
            
                
    return success
        

#Returns False is there was an error pulling the data

async def pull_all_data(is_rt=True):
    global lounge_player_data_ct
    global ct_last_updated
    global lounge_player_data_rt
    global rt_last_updated
    global rt_progress
    global ct_progress
    """
    if in_testing_data_mode:
        if is_rt:
            with open('rts.pkl', "rb") as pickle_in:
                try:
                    lounge_player_data_rt = p.load(pickle_in)
                except:
                    print("Could not read lounge player rts in.")
                    lounge_player_data_rt = {}
                rt_last_updated = datetime.now()
        else:
            with open('cts.pkl', "rb") as pickle_in:
                try:
                    lounge_player_data_ct = p.load(pickle_in)
                except:
                    print("Could not read lounge player cts in.")
                    lounge_player_data_ct = {}
                ct_last_updated = datetime.now()
        return True"""

    all_players = None
    success = True
    main_url = rt_main_url if is_rt else ct_main_url
    new_dict_data = {}
    
    try:
        all_players = await Shared.fetch(main_url)
    except:
        success = False
    data_is_corrupt = all_player_is_corrupt(all_players)
    if data_is_corrupt:
        success = False
    else:
        #do good stuff
        all_players.sort(key=lambda x:x['pid'])
        next_chunk = []
        
        for i, player in enumerate(all_players):
            if player['name'].endswith("_false"):
                continue
            next_chunk.append(player['name'])
            
            
            if len(next_chunk) == chunk_size:
                chunk_success = await pull_chunk(next_chunk, new_dict_data, is_rt)
                if not chunk_success:
                    print("Failed to pull chunk.")
                    success = False
                    break
                next_chunk = []
                if is_rt:
                    rt_progress = round( (i/len(all_players))*100, 1)
                else:
                    ct_progress = round( (i/len(all_players))*100, 1)

    
        else:
            if len(next_chunk) > 0:
                chunk_success = await pull_chunk(next_chunk, new_dict_data, is_rt)
                if not chunk_success:
                    print("Failed to pull chunk.")
                    success = False   
                 
                    
    if success:
        if is_rt:
            lounge_player_data_rt = new_dict_data
            rt_last_updated = datetime.now()
        else:
            lounge_player_data_ct = new_dict_data
            ct_last_updated = datetime.now() 
            
    if is_rt:
        rt_progress = 100.0
    else:
        ct_progress = 100.0
                        
    return success


async def pull_data():
    global currently_pulling
    global lounge_player_data_rt
    global lounge_player_data_ct
    global rt_progress
    global ct_progress
    global global_cached
    currently_pulling = True
    rt_progress = 0.0
    ct_progress = 0.0
    
    #RTs first
    rt_success = await pull_all_data(True)
    rt_progress = 100.0
    await asyncio.sleep(interval_time)
    ct_success = await pull_all_data(False)
    ct_progress = 100.0
    global_cached = {}
    
        
    currently_pulling = False
        
    return rt_success and ct_success


class Leaderboard(object):

    def __init__(self):
        self.last_leaderboard_sent = None
    
    def is_leaderboard_command(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, leaderboard_terms, prefix)
    def can_send_leaderboard(self):
        if self.last_leaderboard_sent == None:
            return True
        time_passed = datetime.now() - self.last_leaderboard_sent
        return time_passed >= LEADERBOARD_WAIT_TIME
    
    def __get_ago_str(self, last_updated):
        last_updated_str = "last updated: "
        how_long_ago = datetime.now() - last_updated
        days = how_long_ago.days
        seconds = int(how_long_ago.total_seconds())
        hours = seconds//3600
        minutes = (seconds//60)%60
        stuffs = []
        if days != 0:
            temp = str(days) + " day"
            if days != 1:
                temp += "s"
            stuffs.append(temp)
        if hours != 0:
            temp = str(hours) + " hour"
            if hours != 1:
                temp += "s"
            stuffs.append(temp)
        if minutes != 0:
            temp = str(minutes) + " minute"
            if minutes != 1:
                temp += "s"
            stuffs.append(temp)
        seconds = seconds % 60
        temp = str(seconds) + " second"
        if seconds != 1:
            temp += "s"
        stuffs.append(temp)
        last_updated_str += ", ".join(stuffs) + " ago"
        return last_updated_str
    
    def get_extra_text(self, is_rt=True):
        total_message = "- Data updates every " + str(int(time_between_pulls.total_seconds())//3600) + " hours"
        cooldown_message = '\n- You can do !leaderboard again in ' + str(int(LEADERBOARD_WAIT_TIME.total_seconds())) + " seconds"
        if is_rt:
            if rt_last_updated != None:
                total_message += "\n- RTs " + self.__get_ago_str(rt_last_updated)
        else:
            if ct_last_updated != None:
                total_message += "\n- CTs " + self.__get_ago_str(ct_last_updated)
            

        if currently_pulling:
            if is_rt:
                total_message += "\n- Currently pulling new data. RT progress: " + str(rt_progress) + "%"
            else:
                total_message += "\n- Currently pulling new data. CT progress: " + str(ct_progress) + "%"
        total_message += cooldown_message
        return total_message
    
    def __get_results(self, command_name, field_name, date_filter, should_reverse, minimum_events_needed, x_number, is_rt=True):
        if is_rt not in global_cached:
            global_cached[is_rt] = {}
            
        if command_name in global_cached[is_rt]:
            return global_cached[is_rt][command_name]
        
        to_sort = []
        player_data = lounge_player_data_rt if is_rt else lounge_player_data_ct
        
        if date_filter:
            date_cutoff = datetime.now() - date_filter_time
            for player in player_data.values():
                if player['total_wars'] < minimum_events_needed:
                    continue
                if player['update_date'] < date_cutoff:
                    continue
                if field_name == 'win_streak' and player['wins10'] < player['win_streak']:
                    continue
                to_sort.append(player)
        else:
            for player in player_data.values():
                if player['total_wars'] < minimum_events_needed:
                    continue
                if field_name == 'win_streak' and player['wins10'] < player['win_streak']:
                    continue
                to_sort.append(player)
            
        to_sort.sort(key=lambda p:p[field_name], reverse=should_reverse)
        results = to_sort[:x_number]
        global_cached[is_rt][command_name] = results
        return results
        
        

    async def send_leaderboard_message(self, message:discord.Message, prefix=Shared.prefix):
        command_end = Shared.strip_prefix_and_command(message.content, leaderboard_terms, prefix).strip().split()
        cooldown_message = '\n\n`You can do !leaderboard again in ' + str(int(LEADERBOARD_WAIT_TIME.total_seconds())) + " seconds`"
        if len(command_end) != 2:
            await message.channel.send("Here's how to use this command: *!leaderboard  <rt/ct>  <stat>*\n**stat** can be any of the following: *" + ",  ".join(stat_terms) + "*" + cooldown_message)
        else:
            if command_end[0].lower() not in leaderboard_type_terms:
                await message.channel.send("Specify a leaderboard type: rt or ct" + cooldown_message)
            else:
                if command_end[1].lower() not in stat_terms:
                    await message.channel.send("Your **stat** was not valid. Here's how to use this command:\n*!leaderboard  <rt/ct>  <stat>*\n**stat** can be any of the following: *" + ",  ".join(stat_terms) + "*" + cooldown_message)
                else:
                    is_rt = command_end[0].lower() == 'rt'
                    still_booting = False
                    if is_rt and lounge_player_data_rt == None:
                        await message.channel.send("The bot just booted up. Player data is still loading for RTs: **" + str(rt_progress) + "%** - This can take several minutes, try again later." + cooldown_message)
                        still_booting = True
                    if not is_rt and lounge_player_data_ct == None:
                        await message.channel.send("The bot just booted up. Player data is still loading for CTs: **" + str(ct_progress) + "%** - This can take several minutes, try again later." + cooldown_message)
                        still_booting = True
                    
                    if not still_booting:
                        field_name, embed_name, date_filter, should_reverse, minimum_events_needed = stat_terms[command_end[1].lower()]
                        results = self.__get_results(command_end[1].lower(), field_name, date_filter, should_reverse, minimum_events_needed, TOP_N_RESULTS, is_rt)
                        embed_name = ("RT - " if is_rt else "CT - ") + embed_name
                        embed = discord.Embed(
                                    title = embed_name,
                                    colour = discord.Colour.dark_blue()
                                )
            
            
                        for player in results:
                            player_name = player['name']
                            data_piece = player[field_name]
                            if isinstance(data_piece, float):
                                if field_name in mult_100_fields:
                                    data_piece = str(round((data_piece*100), 1)) + "%"
                                else:
                                    data_piece = round(data_piece, 1)
                            data_piece = str(data_piece)
                            value_field = "[" + data_piece + "](" + player['url'] + ")"
                            embed.add_field(name=player_name, value=value_field, inline=False)
                        
                        embed.set_footer(text=self.get_extra_text(is_rt))
                        
                        await message.channel.send(embed=embed)
                
        self.last_leaderboard_sent = datetime.now()
        
    async def process_leaderboard_command(self, message:discord.Message, prefix=Shared.prefix):
        if not Shared.has_prefix(message.content, prefix):
            return False
        if self.is_leaderboard_command(message.content, prefix):
            if self.can_send_leaderboard():
                await self.send_leaderboard_message(message, prefix)
        else:
            return False
        return True
    


