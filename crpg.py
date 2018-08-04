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

def sigmoid(x, deriv=False):
    if(deriv==True):
        return x*(1-x)
    return 1/(1+math.exp(-x))

name = {
      "h" :  "head",
      "t" :  "torso",
      "la":  "left arm",
      "ra": "right arm",
      "ll": "left leg",
      "rl": "right leg"
      }
pos = {
      "h" :  [0,1],
      "t" :  [0,0],
      "la":  [1,0],
      "ra": [-1,0],
      "ll": [1,-1],
      "rl":[-1,-1]
      }
size = {
      "h" :  0.06,
      "t" :  0.3,
      "la":  0.1,
      "ra": 0.1,
      "ll": 0.15,
      "rl": 0.15
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
    def __init__(self, info, isPlayer=True):
        self.ai = AI(self)
        self.weapon = Item("steel_spear01", {"amount":1})
        self.isPlayer = isPlayer
        for key in info:
            setattr(self, key, info[key])
        if not "stance" in info:
            self.stance = Stance(self, [0,0,0,0])
        if not "armour" in info:
            self.armour = {
            "h" : Item("skin", {"amount":1}),
            "t" : Item("skin", {"amount":1}),
            "la" : Item("skin", {"amount":1}),
            "ra" : Item("skin", {"amount":1}),
            "ll" : Item("skin", {"amount":1}),
            "rl" : Item("skin", {"amount":1}),
            }
        self.ai = AI(self)

    def isDead(self):
        if self.health["h"] <= 0:
            return True
        if self.health["HP"] <= 0:
            return True
        return False

    def changeEquip(self, itemname):
        matches = [item for item in self.inv if item.name.lower() == itemname.lower()] 
        print(itemname)
        if len(matches) > 0:
            self.weapon = matches[0]
        else:
            self.weapon = [item for item in self.inv if item.name.lower() == "fists"][0]
        self.save()

    def applyDamage(self, wound):
        if wound == None:
            return
        if wound.type == "blunt":
            self.health[wound.location] -= wound.value
        else:
            self.wounds.append(wound)
        self.save()

    def listWounds(self):
        content = ""
        for x in self.wounds:
            content += "{} on {}\n".format(x.type, name[x.location])
        if content == "":
            content = "None"
        return content

    def invmass(self):
        s = 0
        for x in self.inv:
            s += x.mass
        return s

    def save(self):
        if not self.isPlayer:
            savePickle("data/crpg/npcs/{}/info.obj".format(self.ID), self)
        else:
            savePickle("data/crpg/players/{}/info.obj".format(self.ID), self)

class Item:
    def __init__(self, itemID, *info, **kwargs):

        #if id is given, take the properties of default item with that id, if not, properties should be passed in a dictionary
        if itemID == "":
            self.itemID = genID()
        else:
            for key in items[itemID]:
                setattr(self, key, items[itemID][key])
        for d in info:
            for key in d:
                setattr(self, key, d[key])

        for key in kwargs:
            setattr(self, key, kwargs[key])

class AI:
    def __init__(self, player, defend=None, action=None):
        self.player = player
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
            return stab_table[attack.target]
        elif attack.type == "strike":
            return strike_table[attack.target]
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
    def __init__(self, player, code):
        self.x = code[0]*0.3 #-1 left 0 middle 1 right
        self.y = code[1]*0.7 #-1 bottom 0 middle 1 top
        self.z = code[2]*player.proportions["arm"]/3 #0 close 1 neutral 2 forward 3 overextended
        self.line = code[3]
        self.name = str(code)

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
        dz = p_distance - self.stance.z
        dx = self.stance.x - pos[target][0]
        dy = self.stance.y - pos[target][1]
        d1 = math.sqrt(dx*dx+dy*dy)
        self.distance = math.sqrt(dz*dz+d1*d1)

        self.weapon = weapon
        w_overlap = self.weapon.length - self.distance
        if self.weapon.blade["length"] > w_overlap:
            self.overlap = w_overlap
        else:
            self.overlap = self.weapon.blade["length"]
        if atktype == "stab":
            w_acceleration = player.strength["arm"]/weapon.mass
            b_acceleration = player.strength["legs"]/(player.mass+player.invmass()+weapon.mass)
            self.velocity = math.sqrt(2*w_acceleration*self.distance)
            self.velocity += math.sqrt(2*b_acceleration*self.stance.lungelen())
            self.acceleration = w_acceleration + b_acceleration
            self.attack_area = weapon.blade["stab"]["area"]
        
        if atktype == "strike":
            self.acceleration = player.strength["arm"]/weapon.mass
            self.velocity = math.sqrt(2*self.acceleration*self.distance)
            self.attack_area = self.overlap
        self.energy = 1/2*self.weapon.blade["mass"]*self.velocity*self.velocity
        self.momentum = self.weapon.blade["mass"]*self.velocity

class Defense:
    """Determines the effectiveness of an attack."""
    def __init__(self, player, weapon, stance, attack):
        self.type = player.ai.defend(player.weapon, attack)
        self.weapon =  weapon
        self.stance = stance
        self.reaction = player.combat_stats["reactionspeed"]*player.buffs["reaction"]
        if self.type == "b":
            self.destination = pos[attack.target]+[0]

class Wound:
    def __init__(self, _type, location, value, text):
        self.type = _type
        self.value = value
        self.location = location
        self.text = text

    def severity(self):
        if self.type == "cut":
            if self.value[0] > 0.2 or self.value[1] > 0.1:
                return "severe"
        elif self.type == "stab":
            if self.value > 0.2:
                return "severe"
        return "mild"

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
        embed.add_field(name="Stances", value="{}'s stance:{}\n{}'s stance:{}".format(self.p1.name, self.p1.stance.name, self.p2.name, self.p2.stance.name), inline=False)
        
        if self.p1.isPlayer:
            h1 = self.p1.health    
            embed.add_field(name="{}'s Health".format(self.p1.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(h1["HP"]), str(h1["h"]), str(h1["t"]), str(h1["la"]), str(h1["ra"]), str(h1["ll"]), str(h1["rl"])), inline=True)
            embed.add_field(name="{}'s Wounds".format(self.p1.name), value=self.p1.listWounds(), inline=True)
        #embed.add_field(name=" ",value=" ",inline=False)
        if self.p2.isPlayer:
            h2 = self.p2.health
            embed.add_field(name="{}'s Health".format(self.p2.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(h2["HP"]), str(h2["h"]), str(h2["t"]), str(h2["la"]), str(h2["ra"]), str(h2["ll"]), str(h2["rl"])), inline=True)
            embed.add_field(name="{}'s Wounds".format(self.p2.name), value=self.p2.listWounds(), inline=True)
        embed.add_field(name="Battle Log", value="\n".join(self.turns), inline=False)
        return embed

    async def start(self):
        self.message = await self.rpg.bot.send_message(self.channel, embed=self.updatemsg())
        await self.nextTurn()

    async def resolveAttack(self, attack, defense, attacker, defender):
        def success(attack, defense):
            return True
        def calcDamage(attack, armour):
            if attack.overlap == 0:
                damage = Wound("blunt", attack.target, attack.weapon.mass-attack.weapon.blade["mass"], "{} hit {} with the handle of their weapon!".format(attacker.name, defender.name))
                attacker.stance = Stance(defender, pos[attack.target]+[2, 1])
                return damage
            if attack.overlap < 0:
                damage =  Wound("blunt", attack.target, 0, "{} was too far away to use their weapon!".format(attacker.name))
                return damage
            pressure = attack.weapon.blade[attack.type]["sharpness"]/100*attacker.strength["arm"]/attack.attack_area # sharpness applied as a multiplier of pressure, effectively dividing the impact area and thus increasing the imapct pressure
            if pressure > armour.cut_threshold:
                if attack.type == "strike":
                    cut_size = random.random()*size[attack.target]*armour.resistance
                    cut_depth = random.random()*attack.energy*armour.resistance
                    damage = Wound("cut", attack.target, [cut_size, cut_depth], "{} lands a cut on {}'s {}.".format(attacker.name, defender.name, name[attack.target]))
                else:
                    damage = Wound("stab", attack.target, sigmoid(pressure*attack.momentum)*attack.weapon.blade["length"], "{} successfully stabs {} in the {} with their {}.".format(attacker.name, defender.name, name[attack.target], attack.weapon.name))
            return damage
        if success:
            defender.stance = Stance(defender, pos[attack.target]+[0, 0])
            damage = calcDamage(attack, defender.armour[attack.target])
            defender.applyDamage(damage)
        return [attacker, defender, damage.text]

    async def nextTurn(self):
        distance = abs(self.p1.pos)+abs(self.p2.pos)
        if not self.p1.isPlayer:
            action1 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p1.ID), self.channel, "player 1's turn.")
        else:
            action1 = self.p1.ai.action(self)
        if self.p2.isPlayer:
            action2 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p2.ID), self.channel, "player 2's turn.")
        else:
            action2 = self.p2.ai.action(self)
        action1 = action1.split(" ")
        action2 = action2.split(" ")
        if not action1[0].startswith("stance"):
            attack1 = Attack(self.p1, distance, self.p1.weapon, action1[0], action1[1])
        if not action2[0].startswith("stance"):
            attack2 = Attack(self.p2, distance, self.p2.weapon, action2[0], action2[1])
        if not attack1 == None:
            defense2 = Defense(self.p2, self.p2.weapon, self.p2.stance, attack1)
            result1 = await self.resolveAttack(attack1, defense2, self.p1, self.p2)
            self.turns.append(result1[2])
            self.p1 = result1[0]
            self.p2 = result1[1]
        if not attack2 == None and not self.p2.isDead():
            defense1 = Defense(self.p1, self.p1.weapon, self.p1.stance, attack2)
            result2 = await self.resolveAttack(attack2, defense1, self.p2, self.p1)
            self.turns.append(result2[2])
            self.p1 = result2[1]
            self.p2 = result2[0]
        if self.p1.isDead() or self.p2.isDead():
            return [self.p1,self.p2]
        await self.rpg.bot.edit_message(self.message, embed=self.updatemsg())
        return await self.nextTurn()
        
        
class ChillRPG:
    """Class holding game information, methods and player interaction."""
    def __init__(self, bot):
        self.bot = bot
        self.yes = ["yes", "y", "ok", "okay", "yep", "yeah"]
        self.locations = read_folder("locations") #dictionary of all json files in data/crpg/locations/
        self.no = ["no", "n"]
        self.startkits = [[Item("pitchfork01", {"amount":1})],
                          [Item("steel_axe01", {"amount":1})],
                          [Item("steel_spear01", {"amount":1})],
                          [Item("steel_armingsword01", {"amount":1})]]
        self.materials = [Material("mild_steel", True, 70, 370, 8050)]
        self.defaultNPCinfo = fileIO("data/crpg/default_npc.json", "load")
        self.defaultNPCinfo["weapon"] = (Item("steel_axe01", {"amount":1}))

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
            player.save()
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
    async def fight(self, ctx):
        player1 = await self.getPlayer(ctx.message.author.id, ctx)
        player2 = await self.getPlayer(ctx.message.mentions[0].id, ctx)
        fight = Fight(player1, player2, self, ctx.message.channel)
        await fight.start()

    @commands.command(pass_context=True)
    async def fightai(self, ctx):
        player1 = await self.getPlayer(ctx.message.author.id, ctx)
        player2 = Player(self.defaultNPCinfo, isPlayer=False)
        player2.weapon = Item("steel_armingsword01", {"amount":1})
        fight = Fight(player1, player2, self, ctx.message.channel)
        await fight.start()

    @commands.command(pass_context=True)
    async def weapon(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        player.changeEquip(ctx.message.content[8:])
        await self.bot.send_message(ctx.message.channel, embed=discord.Embed(title="Success", description="Set your weapon to {}.".format(player.weapon.name), color=0x16ffeb))

    @commands.command(pass_context=True)
    async def save(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        player.save()

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