'''
Created on Oct 5, 2020

@author: willg
'''
import Shared
import os
import dill as p
import discord
from _datetime import timedelta
from datetime import datetime

dict_data = None


restriction_boss_commands = set(("help",
                                 "restrict_reset",
                                 "addterm", "removeterm",
                                 "addwarterm", "removewarterm",
                                 "mutetime",
                                 "restrict_off", "restrict_on",
                                 "restrict_settings",
                                 "set_war_channel_id",
                                 "set_muted_role_id",
                                 "set_restricted_role_id",
                                 "set_war_restricted_role_id"))

def get_role(guild:discord.Guild, role_id:int):
    mapping, _ = Shared.get_role_mapping(role_id, guild)
    if role_id in mapping:
        return mapping[role_id]
    return None
        
async def settings_menu(message:discord.Message):
    command = Shared.strip_prefix(message.content.lower()).strip()
    if command == "help":
        await message.channel.send(get_help())
    elif command == "restrict_reset":
        load_default_data_settings()
        await message.channel.send("Reset.")
    elif command.startswith("addterm"):
        term = command[len("addterm"):].strip()
        if term == "":
            await message.channel.send("Provide a term to add.")
        else:
            dict_data['whitelistedterms'].add(term)
            await message.channel.send("Added: " + term)
    elif command.startswith("removeterm"):
        term = command[len("removeterm"):].strip()
        if term == "":
            await message.channel.send("Provide a term to remove.")
        elif term not in dict_data['whitelistedterms']:
            await message.channel.send("This was not a previously whitelisted term: " + term)
        else:
            dict_data['whitelistedterms'].remove(term)
            await message.channel.send("Removed whitelisted term: " + term)
    elif command.startswith("addwarterm"):
        term = command[len("addwarterm"):].strip()
        if term == "":
            await message.channel.send("Provide a term to add to allow in war channel.")
        else:
            dict_data['warchatwhitelistedterms'].add(term)
            await message.channel.send("Added (war channel term): " + term)
    elif command.startswith("removewarterm"):
        term = command[len("removewarterm"):].strip()
        if term == "":
            await message.channel.send("Provide a (war channel) term to remove.")
        elif term not in dict_data['warchatwhitelistedterms']:
            await message.channel.send("This was not a previously (war channel) whitelisted term: " + term)
        else:
            dict_data['warchatwhitelistedterms'].remove(term)
            await message.channel.send("Removed (war channel) whitelisted term: " + term)
    elif command.startswith("mutetime"):
        mute_length = command[len("mutetime"):].strip()
        if not mute_length.isnumeric():
            await message.channel.send("Specify the mute length in number of seconds. Example: For a 5 minute mute length: `!mutetime 300`")
        mute_length = int(mute_length)
        if mute_length > 604800:
            await message.channel.send("A maximum of 604800 seconds is allowed for mute length. (This is one week.)")
        else:
            dict_data['mutetime'] = timedelta(seconds=mute_length)
            await message.channel.send("Set mute time to: " + str(mute_length) + " seconds")
    elif command == "restrict_off":
        dict_data['on'] = False
        await message.channel.send("Restriction filter turned off.")
    elif command == "restrict_on":
        dict_data['on'] = True
        await message.channel.send("Restriction filter turned on.")
    elif command == "restrict_settings":
        data_str = get_dict_data_str()
        if len(data_str) < 2000:
            await message.channel.send(get_dict_data_str())
        else:
            for i in range(10):
                this_chunk = data_str[i*2000:(i+1)*2000]
                if this_chunk == "":
                    break
                await message.channel.send(this_chunk)
    elif command.startswith("set_war_channel_id"):
        id_to_set = command[len("set_war_channel_id"):].strip()
        if not id_to_set.isnumeric():
            await message.channel.send("ID must be a number.")
        else:
            dict_data['warchannelid'] = int(id_to_set)
            await message.channel.send("Set war channel id to: " + id_to_set)
    elif command.startswith("set_muted_role_id"):
        id_to_set = command[len("set_muted_role_id"):].strip()
        if not id_to_set.isnumeric():
            await message.channel.send("ID must be a number.")
        else:
            dict_data['mutedroleid'] = int(id_to_set)
            await message.channel.send("Set muted role id to: " + id_to_set)
    elif command.startswith("set_restricted_role_id"):
        id_to_set = command[len("set_restricted_role_id"):].strip()
        if not id_to_set.isnumeric():
            await message.channel.send("ID must be a number.")
        else:
            dict_data['restrictedroleid'] = int(id_to_set)
            await message.channel.send("Set restricted role id to: " + id_to_set)
    elif command.startswith("set_war_restricted_role_id"):
        id_to_set = command[len("set_war_restricted_role_id"):].strip()
        if not id_to_set.isnumeric():
            await message.channel.send("ID must be a number.")
        else:
            dict_data['warchannelrestrictedid'] = int(id_to_set)
            await message.channel.send("Set war restricted role id to: " + id_to_set)

async def restricted_filter(message:discord.Message):
    if Shared.is_boss(message.author) or Shared.is_developer(message.author):
        if Shared.is_in(message.content, restriction_boss_commands, Shared.prefix):
            await settings_menu(message)
            return True
        
    if not dict_data['on']:
        return False
    
    if dict_data['warchannelid'] == message.channel.id:
        if Shared.has_any_role_ids(message.author, dict_data['warchannelrestrictedid']):
            if message.content.strip().lower() not in dict_data['warchatwhitelistedterms']:
                try:
                    await message.delete() #for speed
                    muted_role = get_role(message.guild, dict_data["mutedroleid"])
                    if muted_role == None:
                        return False
                    await message.author.add_roles(muted_role, reason=str(dict_data['mutetime'].total_seconds()/60) + " minute mute: non-whitelisted term used in war channel")
                    dict_data['muted_members'][message.author.id] = datetime.now()
                except:
                    raise
                    pass
                return True
    else:
        if Shared.has_any_role_ids(message.author, dict_data['restrictedroleid']):
            if message.content.strip().lower() not in dict_data['whitelistedterms']:
                try:
                    await message.delete() #for speed
                    muted_role = get_role(message.guild, dict_data["mutedroleid"])
                    if muted_role == None:
                        return False
                    await message.author.add_roles(muted_role, reason=str(dict_data['mutetime'].total_seconds()/60) + " minute mute: non-whitelisted term used in war channel")
                    dict_data['muted_members'][message.author.id] = datetime.now()
                except:
                    pass
                return True
    return False




async def check_muted(guild:discord.Guild):
    if dict_data == None:
        return
    if not dict_data['on']:
        return
    
    muted_role = get_role(guild, dict_data["mutedroleid"])
    if muted_role == None:
        return False
    
    if len(dict_data["muted_members"]) == 0:
        return
    for member in guild.members:
        if member.id in dict_data["muted_members"]:
            mute_time = dict_data["muted_members"][member.id]
            time_passed = datetime.now() - mute_time
            if time_passed >= dict_data["mutetime"]:
                try:
                    await member.remove_roles(muted_role, reason="Restricted mute ended.")
                    del dict_data["muted_members"][member.id]
                except:
                    pass

def get_help():
    str_msg =  "**Only Bosses are allowed to use this feature and change the settings.**\n"
    str_msg += "\n`!addterm [term]` to add a whitelisted term. All terms are not case sensitive. For example, if you add !mmr as whitelisted, !MMR will be allowed too."
    str_msg += "\n`!removeterm [term]` to remove a whitelisted term."
    str_msg += "\n`!addwarterm [term]` to add a whitelisted war term. Not case sensitive."
    str_msg += "\n`!removewarterm [term]` to remove a whitelisted war term."
    str_msg += "\n`!mutetime [totalseconds]` to set the mute length."
    str_msg += "\n`!restrict_off` to turn the restriction filter off."
    str_msg += "\n`!restrict_on` to turn the restriction filter on."
    str_msg += "\n`!set_war_channel_id [channelid]` to set which channel is the war channel"
    str_msg += "\n`!set_muted_role_id [roleid]` to set which role is the muted role to assign"
    str_msg += "\n`!set_restricted_role_id [roleid]` to set which role is the restricted role"
    str_msg += "\n`!set_war_restricted_role_id [roleid]` to set which role is the war restriction role"
    str_msg += "\n`!restrict_settings` to see the current settings for this feature."
    str_msg += "\n`!restrict_reset` to reset to defaults - careful, you'll lose all of your whitelisted terms - okay, I backup everything every 24 hours and could restore everything, but would be a lengthy process!"
    str_msg += "\n`!help` to display this message."
    return str_msg

def get_dict_data_str():
    total_str = ""
    if dict_data == None:
        return "data corrupt"
    total_str += "Restricted feature is on: " + str(dict_data['on'])
    total_str += "\nWhitelisted terms: " + ", ".join(dict_data['whitelistedterms'])
    total_str += "\nWar chat whitelisted terms: " + ", ".join(dict_data['warchatwhitelistedterms'])
    total_str += "\n\nMute time (seconds): " + str(dict_data['mutetime'].total_seconds())
    total_str += "\nWar channel ID: " + str(dict_data['warchannelid'])
    total_str += "\nMuted role ID: " + str(dict_data['mutedroleid'])
    total_str += "\nRestricted role ID: " + str(dict_data['restrictedroleid'])
    total_str += "\nRestricted (war channel) role ID: " + str(dict_data['warchannelrestrictedid'])
    total_str += "\nMuted member (ID, mute time - Pacific Coast Time):\n" + "\n\t".join([str(item[0]) + ", Mute time: " + str(item[1]) for item in dict_data['muted_members'].items()])
    return total_str

def load_default_data_settings():
    global dict_data
    dict_data = {}
    dict_data['whitelistedterms'] = set()
    dict_data['warchatwhitelistedterms'] = set()
    dict_data['mutetime'] = timedelta(minutes=5)
    dict_data['on'] = True
    dict_data['currentlymuted'] = set()
    dict_data['warchannelid'] = -1
    dict_data['mutedroleid'] = -1
    dict_data['restrictedroleid'] = -1
    dict_data['warchannelrestrictedid'] = -1
    dict_data['muted_members'] = {}
    
def load_whitelisted_terms_pickle(backup_path=Shared.restricted_filter_data_pickle_path):
    global dict_data
    load_default_data_settings()
    
    if os.path.exists(backup_path):
        with open(backup_path, "rb") as pickle_in:
            try:
                dict_data = p.load(pickle_in)
            except:
                print("Could not read in pickle for restriction filter.")
                raise
            
def settings_pickle_dump():
    with open(Shared.restricted_filter_data_pickle_path, "wb") as pickle_out:
        try:
            p.dump(dict_data, pickle_out)
        except:
            print("Could not dump pickle for restricted filter.")
            raise

    