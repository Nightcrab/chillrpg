import discord
import os
import json
import random

class Player:
	def __init__(self, id):
        

class Item:
	def __init__(self, info)
	    self.info = info

class Enemy:
	def __init__(self, info, ai=None):
		self.info = info

		if ai == None:
			def base_ai(fight):
				return random.choice(self.info.attacks)
			self.ai = base_ai
		else:
			self.ai = ai

class Fight:
	"""Created whenever a player enters a fight."""
	def __init__(self, player1, player2):
		self.p1 = player1
		self.p2 = player2

class ChillRPG:
	"""Class holding game information and methods."""
	def __init__(self, bot):
		self.bot = bot
