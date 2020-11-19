'''
Created on Sep 14, 2020

@author: willg
'''

import discord
from typing import List, Tuple
from discord.ext import tasks

import TierMogi
import Player
import Shared
import os
import dill as p
import sys
import atexit
import signal
import MMR


testing_server = False
bot_key = None
testing_bot_key = None
pickle_dump_path = "tiers_pickle.pkl"
private_info_file = "private.txt"

pug_lounge_server_id = 387347467332485122

RT_ECHELON_CATEGORY = 389250562836922378
CT_ECHELON_CATEGORY = 520790337443332104
RT_32_TRACK_CATEGORY = 695649588857798686
SUPPORT_CATEGORY = 572901669638242308
MODERATION_CATEGORY = 430167221600518174
UNRANKED_CATEGORY = 650189437434593299
allowed_mogi_categories = [RT_ECHELON_CATEGORY, CT_ECHELON_CATEGORY, RT_32_TRACK_CATEGORY, SUPPORT_CATEGORY, MODERATION_CATEGORY, UNRANKED_CATEGORY]
#mogi_bot_id = 450127943012712448
DEBUGGING = False

if testing_server == True:
    pug_lounge_server_id = 739733336871665696
    allowed_mogi_categories = [740574341187633232]

tier_mogi_instances = None
mmr_channel_instances = {}
tier_instances = {}
client = discord.Client()


def create_mmr_string(players:List[Tuple[int, str, discord.Member]]):
    mmr_str = "**Player List**"
    for index, player in enumerate(players, 1):
        mmr_str += "\n`" + str(index) + ".` "
        mmr_str += player[2].display_name + " (MMR: "
        if player[0] == -1:
            mmr_str += "NAN - Name doesn't match Lounge name"
        else:
            mmr_str += str(player[0])
        mmr_str += ")"
    return mmr_str

@client.event
async def on_message(message: discord.Message):
    
    #mkwxSoup, roomID, rLID = await roomExistsLoop(roomID)
    ##########################################################################################At this point, we know the room exists, and we certainly have rLID. We're not sure if we have the roomID yet though.    
    #ignore everything outside of 5v5 Lounge
    if message.guild == None:
        return
    #ignore your own messages
    if message.author == client.user:
        return
    if message.author.bot:
        return
    if message.guild.id != pug_lounge_server_id:
        return
    if tier_mogi_instances == None:
        return
    
    
    
    channel_id = message.channel.id  
    if message.channel.id not in tier_mogi_instances:
        tier_mogi_instances[channel_id] = TierMogi.TierMogi(message.channel)
        
    if channel_id not in mmr_channel_instances:
        mmr_channel_instances[channel_id] = MMR.MMR()
    
    tier_mogi = tier_mogi_instances[channel_id]
    channel_mmr = mmr_channel_instances[channel_id]
    
    
    #The following snippets of code make the bot more efficient - unfortunately at the cost of making the code less readable
    #TODO: Come back here
    if message.channel.category_id in allowed_mogi_categories:
        await tier_mogi_instances[channel_id].__update__(message)
        
    
    message_str = message.content.strip()
    if message_str == "" or message_str[0] not in Shared.all_prefixes:
        return
    
    #we know that the command starts with ^ or ! now - we check for ^ here and only allow certain commands
    #TODO: Come back here
    if False and message_str[0] == Shared.alternate_prefix:
        if Shared.is_in(message_str, Shared.player_data_commands, prefix=Shared.alternate_prefix):
            was_mmr_command = await channel_mmr.mmr_handle(message, Shared.alternate_prefix)
            if was_mmr_command:
                return
            #It's okay to do these because we already verified their command was a player data command
            was_other_command = await Shared.process_other_command(message, Shared.alternate_prefix)
            if was_other_command:
                return
            await tier_mogi.sent_message(message, tier_mogi_instances, Shared.alternate_prefix)
        return
    
    #Their command starts with !
    #TODO: Come back here
    
    if message.channel.category_id in allowed_mogi_categories:
        if Shared.is_in(message.content, TierMogi.teams_terms, Shared.prefix):
            return
        elif Shared.is_in(message.content, TierMogi.teams_terms, Shared.alternate_prefix):
            await tier_mogi.sent_message(message, tier_mogi_instances, Shared.alternate_prefix)
        else:
            was_mogi_command = await tier_mogi.sent_message(message, tier_mogi_instances, Shared.prefix)
            if was_mogi_command:
                return
        
        
    return #don't check any further - we don't want mmr in Lounge, nor other commands
    
    was_mmr_command = await channel_mmr.mmr_handle(message)
    if was_mmr_command:
        return
    
    
    was_other_command = await Shared.process_other_command(message)
    if was_other_command:
        return
    
    
    
@tasks.loop(seconds=45)
async def routine_tier_checks():
    for _, tier_mogi in tier_mogi_instances.items():
        await tier_mogi.drop_warn_check()

        
@tasks.loop(seconds=60)
async def routine_force_vote_checks():
    if tier_mogi_instances != None:
        for mogi in tier_mogi_instances.values():
            await mogi.force_overtime_pick_check()
    
        
@tasks.loop(hours=24)
async def backup_data():
    Shared.player_fc_pickle_dump()
    Shared.backup_files(Shared.backup_file_list)
       
       
def get_channel(channels, channel_id):
    temp = discord.utils.get(channels, id=channel_id)
    return temp
def get_member(members, member_id):
    temp = discord.utils.get(members, id=member_id)
    return temp

def private_data_init():
    global testing_bot_key
    global bot_key
    with open(private_info_file, "r") as f:
        testing_bot_key = f.readline().strip("\n")
        bot_key = f.readline().strip("\n")
        Shared.google_api_key = f.readline().strip("\n")
        Shared.google_sheet_gid_url = Shared.google_sheets_url_base + Shared.google_sheet_id + "/values:batchGet?" + "key=" + Shared.google_api_key


@client.event
async def on_ready():
    """global user_flag_exceptions
    unlockCheck.start()"""
    global tier_mogi_instances
    
    if tier_mogi_instances == None:
        tier_mogi_instances = {}
        #TODO: COme back here
        if os.path.exists(pickle_dump_path):
            guild = client.get_guild(pug_lounge_server_id)
            members = await guild.fetch_members(limit=None).flatten()
            channels = guild.text_channels
            picklable_dict = {}
            with open(pickle_dump_path, "rb") as pickle_in:
                try:
                    picklable_dict = p.load(pickle_in)
                except:
                    print("Could not read tier instances in.")
                    picklable_dict = {}
                
            new_tier_instances = {}
            for channel_id, picklable_tier_mogi in picklable_dict.items():
                cur_channel = get_channel(channels, picklable_tier_mogi.channel_id)
                if cur_channel == None:
                    continue
                
                mogi_list = []
                player_error = False
                for picklable_player in picklable_tier_mogi.mogi_list:
                    curPlayer = Player.Player(None, None)
                    curMember = get_member(members, picklable_player.member_id)
                    if curMember == None:
                        player_error = True
                    else:
                        curPlayer.reconstruct(picklable_player, curMember)
                        mogi_list.append(curPlayer)
                teams = None
                if picklable_tier_mogi.teams != None:
                    teams = []
                    for team in picklable_tier_mogi.teams:
                        teams.append([])
                        for picklable_player in team:
                            curPlayer = Player.Player(None, None)
                            curMember = get_member(members, picklable_player.member_id)
                            if curMember == None:
                                player_error = True
                            else:
                                curPlayer.reconstruct(picklable_player, curMember)
                                teams[-1].append(curPlayer)
                
                
                author_mapping = None
                if picklable_tier_mogi.author_mapping != None:
                    author_mapping = {}
                    for hashed, author_id in picklable_tier_mogi.author_mapping.items():
                        curMember = get_member(members, author_id)
                        if curMember != None:
                            author_mapping[hashed] = curMember
                            
                curTier = TierMogi.TierMogi(None)
                curTier.reconstruct(mogi_list, cur_channel, teams, author_mapping, picklable_tier_mogi)
                if player_error:
                    curTier.recalculate()
                new_tier_instances[channel_id] = curTier
                
            tier_mogi_instances = new_tier_instances
            
    if Shared.player_fcs == None: 
        Shared.load_player_fc_pickle()
        
    routine_tier_checks.start()
    backup_data.start()
    routine_force_vote_checks.start()
    print("Finished on ready.")
    


def on_exit():
    print("Exiting...")
    global tier_mogi_instances
    global pickle_dump_path
    
    with open(pickle_dump_path, "wb") as pickle_out:
        try:
            mogis = {}
            for channel_id, mogi in tier_mogi_instances.items():
                mogis[channel_id] = mogi.getPicklableTierMogi()
            p.dump(mogis, pickle_out)
        except:
            print("Could not dump pickle for tier instances.")
            Shared.player_fc_pickle_dump()
            raise
        
    Shared.player_fc_pickle_dump()
    

def handler(signum, frame):
    sys.exit()

signal.signal(signal.SIGINT, handler)

atexit.register(on_exit)

private_data_init()
if testing_server == True:
    client.run(testing_bot_key)
else:
    client.run(bot_key)
