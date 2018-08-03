import discord
import os
import shutil
from discord.ext import commands
from .utils.dataIO import fileIO
import random
import glob
import pickle
import re
import math


def genID(size=8, chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".split()):
    return ''.join(random.choice(chars) for _ in range(size))

def savePickle(filename, obj):
    filehandler = open(filename, 'wb')
    pickle.dump(obj, filehandler)
def loadPickle(filename):
    filehandler = open(filename, 'rb')
    return pickle.load(filehandler)
pos = {
      "h" :  [0,1],
      "t" :  [0,0],
      "la":  [1,0],
      "ra": [-1,0],
      "ll": [1,-1],
      "rl":[-1,-1]
      }

def distance(pos1, pos2):
    x1 = pos1[0]
    y1 = pos1[1]
    z1 = pos1[2]
    x2 = pos2[0]
    y2 = pos2[1]
    z2 = pos2[2]
    d1 = math.sqrt((x2 - x1)*(x2 - x1)+(y2 - y1)*(y2 - y1))
    return math.sqrt(d1*d1+(z2 - z1)*(z2 - z1))

class Player:
    def __init__(self, info):
        self.ai = AI()
        self.isPlayer = True
        for key in info:
            setattr(self, key, info[key])

    def isDead(self):
        if self.health.h <= 0:
            return True
        if self.health.HP <= 0:
            return True
        return False

    def changeEquip(self, itemname):
        matches = [item for item in self.inv if item.name.lower() == itemname.lower()] 
        if len(matches) > 0:
            self.weapon = matches[0]
        else:
            self.weapon = [item for item in self.inv if item.name.lower() == "fists"][0]

    async def save(self):
        savePickle("data/crpg/players/{}/info.obj".format(self.ID), self)

class Item:
    def __init__(self, itemID, *info, **kwargs):

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

class AI:
    def __init__(self, defend=None, action=None):
        return
    def defend(self, weapon, attack):
        stab_table = {
        "la" : "mr", #left arm, move right
        "ra" : "ml",
        "t" : "pl", #torso, parry left
        "h" : "pr"
        }
        strike_table = {
        "la" : "pl",
        "ra" : "pr",
        "t" : "pu",
        "h" : "pl"
        }
        if attack.type == "stab":
            return Defense(stab_table[attack.target])
        elif attack.type == "strike":
            return Defense(strike_table[attack.target])
    def action(self, env):
        return random.choice(["stab ", "strike "])+random.choice(["h","t"])

class Enemy:
    def __init__(self, info, ai=None):
        self.info = info
        self.isPlayer = False

        if ai == None:
            self.ai = AI()
        else:
            self.ai = ai

class Stance:
    def __init__(self, player, string):
        self.code = string.split("")
        self.x = int(code[0])*0.3 #-1 left 0 middle 1 right
        self.y = int(code[1])*0.7 #-1 bottom 0 middle 1 top
        self.z = int(code[2])*player.proportions["arm"]/3 #0 close 1 neutral 2 forward 3 overextended

    def lungelen(self):
        return 0

class Material:
    def __init__(self, name, brittle, tensile, toughness, density):
        self.name = name
        self.brittle = brittle
        self.tensile = tensile
        self.toughness = toughness
        self.density = density

class Attack:
    """An attack, usually countered with a defense."""
    def __init__(self, player, p_distance, weapon, atktype, target):
        self.type = atktype
        self.stance = player.stance
        self.target = target
        self.dz = p_distance - self.stance.z
        self.dx = self.stance.x - pos[target][0]
        self.dy = self.stance.y - pos[target][1]
        self.d1 = math.sqrt(dx*dx+dy*dy)
        self.distance = math.sqrt(dz*dz+d1*d1)

        self.weapon = weapon
        if atktype == "stab":
            w_acceleration = player.strength.arm/weapon.mass
            b_acceleration = player.strength.leg/(player.mass+player.invmass+weapon.mass)
            self.velocity = math.sqrt(2*w_acceleration*self.distance)
            self.velocity += math.sqrt(2*b_acceleration*self.stance.lungelen())
            self.acceleration = w_acceleration + b_acceleration
            self.attack_area = weapon.blade["stab"]["area"]
        
        if atktype == "strike":
            self.acceleration = player.strength.arm/weapon.mass
            self.velocity = math.sqrt(2*acceleration*self.distance)
            if weapon.type == sword:
                self.attack_area = weapon.length - distance
            else:
                self.attack_area = weapon.blade["strike"]["area"]
        self.energy = 1/2*mass*velocity*velocity

class Defense:
    """Determines the effectiveness of an attack."""
    def __init__(self, player, weapon, stance, attack):
        self.type = player.ai.defend(player.weapon, attack)
        self.weapon =  weapon
        self.stance = stance
        self.reaction = player.combat_stats.reactionspeed*player.buffs.reaction
        if self.type == "b":
            self.destination = pos[attack.target]

class Fight:
    """Created whenever a player enters a fight."""
    def __init__(self, player1, player2, chillrpg, channel):
        self.p1 = player1
        self.p2 = player2
        self.p1.pos = -2
        self.p2.pos = 2
        self.rpg = chillrpg
        self.channel = channel
        self.turns = ["The battle began between {} and {}.".format(self.p1.name, self.p2.name)]

    def updatemsg(self):
        description = "you're in a fight, defend yourself m8"
        embed = discord.Embed(title="{} vs {}".format(self.p1.name, self.p2.name), description=description, color=0x16ff64)
        embed.add_field(title="Stances", value="{}'s stance:{}\n{}'s stance:".format(self.p1.stance, self.p2.stance), inline=False)
        
        if self.p1.isPlayer:
            h1 = self.p1.health
            embed.add_field(title="{}'s' Health".format(self.p1.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(h1.HP, h1.h, h1.t, h1.la, h1.ra, h1.ll, h1.rl), inline=False)
        if self.p2.isPlayer:
            h2 = self.p2.health
            embed.add_field(title="{}'s' Health".format(self.p2.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(h2.HP, h2.h, h2.t, h2.la, h2.ra, h2.ll, h2.rl), inline=False)
        embed.add_field(title="Battle Log", value="\n".join(self.turns), inline=False)
        return embed

    async def start(self):
        self.message = await self.rpg.bot.send_message(self.channel, embed=self.updatemsg())
        self.nextTurn()

    async def resolveAttack(self, attack, defense, attacker, defender):
        def success(attack, defense):
            return True
        def calcDamage(attack, armour):
            pressure = attack.weapon.blade[attack.type]["sharpness"]/100*attacker.strength.arm/attack.weapon.blade[attack.type]["area"] # sharpness applied as a multiplier of pressure, effectively dividing the impact area and thus increasing the imapct pressure
            cut_factor = attack.attack_area*attack.velocity/attack.stance.z
        if success:
            defender.stance = Stance(defender, "".join(pos[attack.target]+[0]))

    async def nextTurn(self):
        distance = abs(self.p1.pos)+abs(self.p2.pos)
        if self.p1.isPlayer:
            action1 = await self.rpg.promptUser(self.bot.get_user_info(self.p1.id), channel)
        else:
            action1 = await self.p1.ai.action(self)
        if self.p2.isPlayer:
            action2 = await self.rpg.promptUser(self.bot.get_user_info(self.p2.id), channel)
        else:
            action2 = await self.p2.ai.action(self)
        action1 = action1.split(" ")
        action2 = action2.split(" ")
        if not action1[0].startsWith("stance"):
            attack1 = Attack(p1, distance, p1.weapon, action1[0], action1[1])
        if not action2[0].startsWith("stance"):
            attack2 = Attack(p2, distance, p2.weapon, action2[0], action2[1])
        if not attack1 == None:
            defense2 = self.p2.ai.defend(p2.weapon, attack1)
            result = await resolveAttack(attack1, defense2, self.p1.health)
            self.p1 = result[0]
            self.p2 = result[1]
        if not attack2 == None and not self.p2.isDead():
            defense1 = self.p1.ai.defend(p1.weapon, attack2)
            result = await resolveAttack(attack1, defense2, self.p2, self.p1)
            self.p1 = result[1]
            self.p2 = result[0]
        if self.p1.isDead() or self.p2.isDead():
            return [self.p1,self.p2]
        return await self.turn()
        
        
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
        self.materials = [Material("mild_steel", True, 70, 370, 8050)]

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
            return loadPickle("data/crpg/players/{}/info.obj".format(ID))
        else:
            prompt = "You haven't created a character yet, or your previous one is deceased. Would you like to create a new character?"
            response = await self.promptUser(ctx.message.author, ctx.message.channel, prompt)
            if response.lower() in self.yes:
                return await self.newPlayer(ctx.message.author, ctx.message.channel)

    async def newPlayer(self, user, channel): #Initiate character creation
        ID = user.id

        info = fileIO("data/crpg/default_player.json", "load")
        os.makedirs("data/crpg/players/{}".format(ID))

        await self.bot.send_message(channel, "Welcome to character creation.")
        info["ID"] = ID
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
        fist = {
            "name":"Fists",
            "type":"knuckledusters",
            "length": info["proportions"]["arm"],
            "mass": 0.0065*info["mass"],
            "balance":70,
            "blade": {
                "mass": 0.0065,
                "length":0.04,
                "stab": {
                    "area" : 5,
                    "sharpness" : 10
                }
            },
            "attacks": {
                "stab":"Punch"
            }
        }
        info["inv"].append(Item("", fist, {"amount":1}))
        confirm = await self.promptUser(user, channel, "Does the following describe your new character? ```{} is a {} year old {}. They have no skills or particular beneficial character traits.```".format(info["name"], info["age"], info["gender"]))
        if confirm.lower() in self.yes:
            player = Player(info)
            await player.save()
            return player
        else:
            await self.bot.send_message(channel, "Restarting character creation...")
            return await self.newPlayer(ID, channel)

    async def promptUser(self, author, channel, prompt=None):
        if not prompt == None:
            await self.bot.send_message(channel, prompt)
        response = await self.bot.wait_for_message(author=author, channel=channel)
        return response.content

    async def newFight(self, p1, p2, ctx):
        return Fight(p1, p2, self, ctx.message.channel)

    def listItems(self, inv):
        content = ""
        for item in inv:
            content += "\n{} x {}".format(item.name, item.amount)
        return content

    def listStats(self, player):
        content = "Health: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n"

    def statusEmbed(self, player):
        embed = discord.Embed(title="{}'s Status".format(player.name), color=0x16ff64)
        embed.add_field(name="Stats", value="Health: {}\nStamina: {}\nFatigue: {}\nLevel: {}\nBalance: {}\n".format(player.health["HP"], player.stamina, player.fatigue, player.level, player.balance), inline=False)
        embed.add_field(name="Location", value="{}".format(self.locations[player.location]["description"]), inline=False)
        return embed

    @commands.command(pass_context=True)
    async def inventory(self, ctx):
        embed = discord.Embed(title="Inventory", description=self.listItems((await self.getPlayer(ctx.message.author.id, ctx)).inv), color=0x16ffeb)
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True)
    async def status(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        await self.bot.send_message(ctx.message.channel, embed=self.statusEmbed(player))

    @commands.command(pass_context=True)
    async def weapon(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        player.changeEquip(ctx.message.content[7:])
        await self.bot.send_message(ctx.message.channel, embed=discord.Embed(title="Success", description="Set your weapon to {}.".format(player.weapon.name), color=0x16ffeb))

    @commands.command(pass_context=True)
    async def save(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        await player.save()

    @commands.command(pass_context=True)
    async def begin(self, ctx):
        if os.path.isdir("data/crpg/players/{}".format(ctx.message.author.id)):
            confirm = await self.promptUser(ctx.message.author, ctx.message.channel, "Are you sure you wish to recreate your character? Your old one will become deceased and irretrievable.")
            if confirm.lower() in self.yes:
                shutil.rmtree("data/crpg/players/{}".format(ctx.message.author.id))
            else:
                await self.bot.send_message(ctx.message.channel, "Cancelled character recreation.")
                return
        player = await self.newPlayer(ctx.message.author, ctx.message.channel)
        await self.bot.send_message(ctx.message.channel, embed=self.statusEmbed(player))

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