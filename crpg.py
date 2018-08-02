import discord
import os
import shutil
from discord.ext import commands
from .utils.dataIO import fileIO
import random
import glob
import re

pi = 3.1415

def genID(size=8, chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".split()):
    return ''.join(random.choice(chars) for _ in range(size))

class Player:
    def __init__(self, info):
        for key in info:
            setattr(self, key, info[key])

    async def save(self):
        fileIO("data/crpg/players/{}/info.json".format(id), "save", self.info)

class Item:
    def __init__(self, itemID="", *info, **kwargs):

        #if id is given, take the properties of default item with that id, if not, properties should be passed in a dictionary
        if itemID == "":
            self.itemID = genID()
        else:
            print(items)
            for key in items[itemID]:
                setattr(self, key, items[itemID][key])
        for d in info:
            for key in d:
                setattr(self, key, d[key])

        for key in kwargs:
            setattr(self, key, kwargs[key])

class Enemy:
    def __init__(self, info, ai=None):
        self.info = info

        if ai == None:
            def base_ai(fight):
                return random.choice(self.info.attacks)
            self.ai = base_ai
        else:
            self.ai = ai

class Attack:
    """An attack, usually countered with a defense."""
    def __init__(self, player, weapon):
        self.acceleration = 2*pi*weapon.length

class Defense:
    """Determines the effectiveness of an attack."""

class Fight:
    """Created whenever a player enters a fight."""
    def __init__(self, player1, player2):
        self.p1 = player1
        self.p2 = player2

class ChillRPG:
    """Class holding game information, methods and player interaction."""
    def __init__(self, bot):
        self.bot = bot
        self.yes = ["yes", "y", "ok", "okay", "yep", "yeah"]
        self.locations = read_folder("locations") #dictionary of all json files in data/crpg/locations/
        self.no = ["no", "n"]
        self.startkits = [[Item("pitchfork01", {"amount":1})],
                          [Item("steel_axe01", {"amount":1})],
                          [Item("steel_spear01", {"amount":1})]]

    def refreshInv(self, inv):
        for x in inv.length:
            if x.amount == 0:
                del x

    async def addItem(self, inv, item):
        for x in inv:
            if x.id == item.id:
                x.amount += 1
                return
        inv.append(item)

    async def getPlayer(self, ID, ctx): #Get a user's character, if it exists
        if os.path.exists("data/crpg/players/{}".format(ID)):
            info = fileIO("data/crpg/players/{}/info.json".format(ID), "load")
            return Player(info)
        else:
            prompt = "You haven't created a character yet, or your previous one is deceased. Would you like to create a new character?"
            response = await self.promptUser(ctx.message.author, ctx.message.channel, prompt)
            if response.lower() in yes:
                return await self.newPlayer(ID, ctx.message.channel)

    async def newPlayer(self, user, channel): #Initiate character creation
        ID = user.id

        info = fileIO("data/crpg/default_player.json", "load")
        os.makedirs("data/crpg/players/{}".format(ID))
        fileIO("data/crpg/players/{}/info.json".format(ID), "save", info)

        await self.bot.send_message(channel, "Welcome to character creation.")
        info["name"] = await self.promptUser(user, channel, "What will your name be?")
        info["age"] = await self.promptUser(user, channel, "How old are you (in years)?")
        info["gender"] = await self.promptUser(user, channel, "What will your gender be?")
        info["gender"] = info["gender"].lower()
        history = await self.promptUser(user, channel, "What is your background? Respond with a number.\n```0. Peasant\n1. Lumberjack\n2. Deserter```")
        if not history.isdigit():
            history = "0"
        history = int(history)
        start_buff = await self.promptUser(user, channel, "What trait would you like to begin with? Respond with a number.\n```0. None```")

        if history == None or history < 0 or history > len(self.startkits)+1:
            history = 0
        info["inv"] = self.startkits[history]
        confirm = await self.promptUser(user, channel, "Does the following describe your new character? ```{} is a {} year old {}. They have no skills or particular beneficial character traits.```".format(info["name"], info["age"], info["gender"]))
        if confirm.lower() in self.yes:
            player = Player(info)
            player.save()
            return player
        else:
            await self.bot.send_message(channel, "Restarting character creation...")
            return await self.newPlayer(ID, channel)

    async def promptUser(self, author, channel, prompt):
        await self.bot.send_message(channel, prompt)
        response = await self.bot.wait_for_message(author=author, channel=channel)
        return response.content

    def listItems(self, inv):
        content = ""
        for item in inv:
            content += "{} x {}".format(item.name, item.amount)

    def status(self, player):
        embed = discord.Embed(title="{}'s Status".format(player.name), color=0x16ff64)
        embed.add_field(name="Stats", value="Health:{}\nStamina:{}\nFatigue:{}\nLevel:{}\nBalance:{}\n".format(player.HP, player.stamina, player.fatigue, player.level, player.balance), inline=False)
        embed.add_field(name="Inventory", value=self.listItems(player.inventory), inline=False)
        embed.add_field(name="Location", value="{}".format(self.locations[player.location].description), inline=False)
        return embed

    @commands.command(pass_context=True)
    async def begin(self, ctx):
        if os.path.isdir("data/crpg/players/{}".format(ctx.message.author.id)):
            confirm = await promptUser(ctx.message.author, ctx.message.channel, "Are you sure you wish to recreate your character? Your old one will become deceased and irretrievable.")
            if confirm.lower() in self.yes:
                shutil.rmtree("data/crpg/players/{}".format(ctx.message.author.id))
            else:
                await self.bot.send_message(ctx.message.channel, "Cancelled character recreation.")
                return
        player = await self.newPlayer(ctx.message.author, ctx.message.channel)
        await self.bot.send_message(ctx.message.channel, embed=self.status(player))

def check_folders():
    if not os.path.exists("data/crpg"):
        print("Creating data/crpg folder...")
        os.makedirs("data/crpg/items/weapons")
        os.makedirs("data/crpg/enemies")
        os.makedirs("data/crpg/locations")
        os.makedirs("data/crpg/items/misc")
        os.makedirs("data/crpg/items/armour")
        os.makedirs("data/crpg/players")
        fileIO("data/crpg/default_player.json", "save", {})

def read_folder(path):
    d = {}
    print("....")
    for filename in glob.glob("data/crpg/{}/*.json".format(path)):
        d[os.path.basename(filename)[:-5]] = fileIO(filename, "load")
    return d     

def setup(bot):
    global items
    items = read_folder("items/*")
    n = ChillRPG(bot)
    bot.add_cog(n)
