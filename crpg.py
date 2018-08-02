import discord
import os
from discord.ext import commands
from .utils.dataIO import fileIO
import random

def genID(size=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class Player:
	def __init__(self, info):

class Item:
	def __init__(self, itemID=None, *info, **kwargs):

		#if id is given, take the properties of default item with that id, if not, properties should be passed in a dictionary
		if itemID == None:
			self.itemID = genID()
		else:
			for key in items[itemID]
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
		self.no = ["no", "n"]
		self.startkits = [[Item("pitchfork01", 1)],
						  [Item("steel_axe01", 1)],
						  [Item("steel_spear01", 1)]]

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

	async def getPlayer(self, id, ctx): #Get a user's character, if it exists
		if os.path.exists("data/crpg/players/{}".format(id)):
        	info = fileIO("data/crpg/players/{}/info.json".format(id), "load")
			return Player(info)
        else:
            prompt = "You haven't created a character yet, or your previous one is deceased. Would you like to create a new character?"
        	response = await self.promptUser(ctx.message.author, ctx.message.channel, prompt)
        	if response.lower() in yes:
        		return await self.newPlayer(id, ctx)

    async def newPlayer(self, ID, channel): #Initiate character creation
    	user = self.bot.get_user_info(ID)

    	info = fileIO("data/crpg/default_player.json", "load")
        os.makedirs("data/crpg/players/{}".format(id))
        fileIO("data/crpg/players/{}/info.json".format(id), "save", info)

    	await self.bot.send_message(channel, "Welcome to character creation.")
    	info["Name"] = await self.promptUser(user, channel, "What will your name be?")
    	info["Age"] = await self.promptUser(user, channel, "How old are you (in years)?")
    	info["Gender"] = await self.promptUser(user, channel, "What will your gender be?").lower()
    	history = await self.promptUser(user, channel, "What is your background? Respond with a number.\n```0. Peasant\n1. Lumberjack\n2. Deserter```")
    	if not history.isdigit():
    		history = "0"
    	history = int(history)
    	start_buff = await self.promptUser(user, channel, "What trait would you like to begin with? Respond with a number.\n```0. None```")

    	if history == None or history < 0 or history > len(self.startkits)+1:
    		history = 0
    	info["inv"] = self.startkits[history]
    	confirm = await self.promptUser(user, channel, "Does the following describe your new character? ```{} is a {} year old {}. They have no skills or particular beneficial character traits.```".format(info["Name"], info["Age"], info["Gender"]))
    	if confirm.lower() in self.yes:
			player = Player(info)
			return await self.savePlayer(player)
		else:
			await self.bot.send_message(channel, "Restarting character creation...")
			return await self.newPlayer(ID, channel)

    async def promptUser(self, author, channel, prompt):
    	await self.bot.send_message(channel, prompt)
    	return await self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel)

    async def savePlayer(self, player):
    	fileIO("data/crpg/players/{}/info.json".format(id), "save", info)
    	return player

def check_folders():
    if not os.path.exists("data/crpg"):
        print("Creating data/crpg folder...")
        os.makedirs("data/crpg/items/weapons")
        os.makedirs("data/crpg/enemies")
        os.makedirs("data/crpg/items/misc")
        os.makedirs("data/crpg/items/armour")
        os.makedirs("data/crpg/players")
        fileIO("data/crpg/default_player.json".format(id), "save", {})

def setup(bot):
    global items
    check_folders()
    n = ChillRPG(bot)
    bot.add_cog(n)
