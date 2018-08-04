import discord
import os
import shutil
from discord.ext import commands
from .utils.dataIO import fileIO
import random
import glob
import pickle
import time
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
      "h" :  [0,0.4],
      "t" :  [0,0],
      "la":  [0.2,0],
      "ra": [-0.2,0],
      "ll": [0.5,-0.5],
      "rl":[-0.5,-0.5]
      }
size = {
      "h" :  0.06,
      "t" :  0.3,
      "la":  0.1,
      "ra": 0.1,
      "ll": 0.15,
      "rl": 0.15
      }

def distance3D(pos1, pos2):
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
        self.weapon = Item("fist", {"amount":2})
        self.isPlayer = isPlayer
        self.combat_stats["reflex_speed"] = 0.9
        self.lastUpdate = time.time()
        for key in info:
            setattr(self, key, info[key])
        if not "stance" in info:
            self.stance = Stance(self, [0,0,0,1])
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
            self.weapon = [item for item in self.inv if item.name.lower() == "fist"][0]
        self.save()

    def applyDamage(self, wound):
        limb_damage_modifier = 1.4
        if wound == None:
            return
        if wound.type == "blunt":
            self.health[wound.location] -= wound.value
        else:
            self.health[wound.location] -= wound.value[1]*limb_damage_modifier
            self.wounds.append(wound)
        self.save()

    def listWounds(self):
        content = ""
        for x in self.wounds:
            if not hasattr(x, 'bleed'):
                x.bleed = 0
            content += "{} on {}, bleeding {} HP per second\n".format(x.type, name[x.location], round(x.bleed, 5))
        if content == "":
            content = "None"
        return content

    def update(self):
        if not hasattr(self, "lastUpdate"):
            self.lastUpdate = time.time()
        for x in self.wounds:
            if x.bleed > 0:
                self.health["HP"] -= x.bleed * (time.time() - self.lastUpdate)
        if self.health["HP"] < 0:
            self.health["HP"] = 0
        self.lastUpdate = time.time()

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
        self.amount = 1
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

        if not hasattr(self, "description"):
            self.description = "No description."

    def getMoves(self):
        content = ""
        for key in self.attacks.keys():
            content += key+"\n"
        return content

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
        return "b"
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
        self.z = code[2]*player.proportions["arm"]/4 #1 close 2 neutral 3 forward 4 overextended
        self.line = code[3]
        self.name = str([self.x,self.y,self.z])

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
            self.velocity = math.sqrt(2*w_acceleration*(self.distance+self.stance.lungelen()))
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
        def limb_lag(health):
            x = (100-health)
            return 5 ** (x/10-2)
        self.reaction = player.combat_stats["reactionspeed"]*player.buffs["reaction"]+limb_lag(player.health[attack.target])
        self.destination = pos[attack.target]+[0]
        distance = distance3D([self.stance.x, self.stance.y, self.stance.z], destination)
        velocity = player.combat_stats["reflex_speed"]*weapon.balance/100

class Wound:
    def __init__(self, _type, location, value, text):
        self.type = _type
        self.value = value
        self.location = location
        self.text = text
        self.bleed = 0
        bloodloss_modifier = 0.2
        print(value)
        if self.type == "cut":
            self.bleed = self.value[0]*self.value[1]*bloodloss_modifier
        if self.type == "stab":
            self.bleed = self.value*bloodloss_modifier

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
        self.p1.pos = -0.2
        self.p2.pos = 0.2
        self.distance = abs(self.p1.pos)+abs(self.p2.pos)
        self.rpg = chillrpg
        self.channel = channel
        self.turns = ["The battle began between {} and {}.".format(self.p1.name, self.p2.name)]

    def updatemsg(self):
        description = "you're in a fight, defend yourself m8"
        embed = discord.Embed(title="{} vs {}".format(self.p1.name, self.p2.name), description=description, color=0x16ff64)
        embed.add_field(name="Stances", value="{}'s stance: {}\n{}'s stance: {}\n\nDistance: {} m".format(self.p1.name, self.p1.stance.name, self.p2.name, self.p2.stance.name, self.distance), inline=False)
        
        if self.p1.isPlayer:
            h1 = self.p1.health    
            embed.add_field(name="{}'s Health".format(self.p1.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(round(h1["HP"], 2)), str(round(h1["h"], 2)), str(round(h1["t"], 2)), str(round(h1["la"], 2)), str(round(h1["ra"], 2)), str(round(h1["ll"], 2)), str(round(h1["rl"], 2))), inline=True)
            embed.add_field(name="{}'s Wounds".format(self.p1.name), value=self.p1.listWounds(), inline=True)
        #embed.add_field(name=" ",value=" ",inline=False)
        if self.p2.isPlayer:
            h2 = self.p2.health
            embed.add_field(name="{}'s Health".format(self.p2.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(round(h2["HP"], 2)), str(round(h2["h"], 2)), str(round(h2["t"], 2)), str(round(h2["la"], 2)), str(round(h2["ra"], 2)), str(round(h2["ll"], 2)), str(round(h2["rl"], 2))), inline=True)
            embed.add_field(name="{}'s Wounds".format(self.p2.name), value=self.p2.listWounds(), inline=True)
        embed.add_field(name="Battle Log", value="\n".join(self.turns), inline=False)
        if self.p1.isPlayer:
            embed.add_field(name="{}'s Moves".format(self.p1.name), value=self.p1.weapon.getMoves(), inline=False)
        if self.p2.isPlayer:
            embed.add_field(name="{}'s Moves".format(self.p2.name), value=self.p2.weapon.getMoves(), inline=False)
        return embed

    async def start(self):
        self.message = await self.rpg.bot.send_message(self.channel, embed=self.updatemsg())
        return await self.nextTurn()

    async def resolveAttack(self, attack, defense, attacker, defender):
        def success(attack, defense):
            def_time = 
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
                    cut_size = random.random()*size[attack.target]*armour.cut_resistance
                    cut_depth = random.random()*attack.energy*armour.cut_resistance
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
        self.distance = abs(self.p1.pos)+abs(self.p2.pos)
        distance = self.distance
        if self.p1.isDead() or self.p2.isDead():
            return [self.p1,self.p2]
        if self.p1.isPlayer:
            action1 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p1.ID), self.channel, "{}'s turn. They have 10 seconds to respond.".format(self.p1.name))
            if not action2 == None:
                action1 = action1.split(" ")
                if not action1[0].lower() in self.p1.weapon.attacks:
                    action1 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p1.ID), self.channel, "That's not a move you can do. You took no action this turn.")
                action1 = [self.p1.weapon.attacks[action1[0].lower()]]+[action1[1]]
            else:
                action1 = ["defend", "t"]
        else:
            action1 = self.p1.ai.action(self)
        if self.p2.isPlayer:
            action2 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p2.ID), self.channel, "{}'s turn. They have 10 seconds to respond.".format(self.p2.name))
            if not action2 == None:
                action2 = action2.split(" ")
                if not action2[0].lower() in self.p2.weapon.attacks:
                    action2 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p2.ID), self.channel, "That's not a move you can do. You took no action this turn.")
                    action2 = 
                action2 = [self.p2.weapon.attacks[action2[0].lower()]]+[action2[1]]
            else:
                action2 = ["defend","t"]
        else:
            action2 = self.p2.ai.action(self)
        if action1[0] == "defend":
            self.p1.buffs["reactionspeed"] = 0.7
        else:
            self.p1.buffs["reactionspeed"] = 1
        if ation2[0] == "defend":
            self.p2.buffs["reactionspeed"] = 0.7
        else:
            self.p1.buffs["reactionspeed"] = 1
        if not action1[0].startswith("defend"):
            attack1 = Attack(self.p1, distance, self.p1.weapon, action1[0], action1[1])
        if not action2[0].startswith("defend"):
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
        self.p1.update()
        self.p2.update()
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
        self.startInv = [Item("fist", {"amount":2})]
        self.materials = [Material("mild_steel", True, 70, 370, 8050)]
        self.defaultNPCinfo = fileIO("data/crpg/default_npc.json", "load")
        self.defaultNPCinfo["weapon"] = (Item("steel_axe01", {"amount":1}))
        self.players = {}

    def refreshInv(self, inv):
        for x in inv.length:
            if x.amount == 0:
                del x

    def unloadPlayer(self, ID):
        if not ID in self.players:
            return
        del(self.players[ID])

    async def addItem(self, inv, item):
        for x in inv:
            if x.id == item.id:
                x.amount += 1
                return
        inv.append(item)

    async def getPlayer(self, ID, ctx): #Get a user's character, if it exists
        if ID in self.players:
            self.players[ID].update()
            return self.players[ID]
        if os.path.exists("data/crpg/players/{}".format(ID)):
            self.players[ID] = loadPickle("data/crpg/players/{}/info.obj".format(ID))
            self.players[ID].update()
            return self.players[ID]
        else:
            prompt = "You haven't created a character yet, or your previous one is deceased. Would you like to create a new character?"
            response = await self.promptUser(ctx.message.author, ctx.message.channel, prompt)
            if response.lower() in self.yes:
                return await self.newPlayer(ctx.message.author, ctx.message.channel)

    async def newPlayer(self, user, channel): #Initiate character creation
        ID = user.id

        self.unloadPlayer(ID)

        info = fileIO("data/crpg/default_player.json", "load")
        os.makedirs("data/crpg/players/{}".format(ID))

        await self.bot.send_message(channel, "Welcome to character creation.")
        info["ID"] = ID
        info["name"] = await self.promptUser(user, channel, "What will your name be?")
        info["age"] = await self.promptUser(user, channel, "How old are you (in years)?")
        info["gender"] = await self.promptUser(user, channel, "What will your gender be?")
        info["gender"] = info["gender"].lower()
        history = await self.promptUser(user, channel, "What is your background? Respond with a number.\n```0. Peasant\n1. Lumberjack\n2. Deserter\n3. Man-at-arms```")
        if not history.isdigit():
            history = "0"
        history = int(history)
        start_buff = await self.promptUser(user, channel, "What trait would you like to begin with? Respond with a number.\n```0. None```")

        if history == None or history < 0 or history > len(self.startkits)+1:
            history = 0
        info["inv"] = self.startkits[history]
        info["inv"].extend(self.startInv)
        confirm = await self.promptUser(user, channel, "Does the following describe your new character? ```{} is a {} year old {}. They have no skills or particular beneficial character traits.```".format(info["name"], info["age"], info["gender"]))
        if confirm.lower() in self.yes:
            player = Player(info)
            player.save()
            return player
        else:
            await self.bot.send_message(channel, "Restarting character creation...")
            return await self.newPlayer(user, channel)

    async def promptUser(self, author, channel, prompt=None, timelimit=None):
        if not prompt == None:
            await self.bot.send_message(channel, prompt)
        response = await self.bot.wait_for_message(timeout=timelimit, author=author, channel=channel)
        return response.content

    async def newFight(self, p1, p2, ctx):
        return Fight(p1, p2, self, ctx.message.channel)

    def listItems(self, inv):
        print(inv)
        content = ""
        for item in inv:
            content += "\n{} x {}".format(item.name, item.amount)
        return content

    def listStats(self, player):
        content = "Health: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n"

    def statusEmbed(self, player):
        embed = discord.Embed(title="{}'s Status".format(player.name), color=0x16ff64)
        embed.add_field(name="Stats", value="Health: {}\nStamina: {}\nFatigue: {}\nLevel: {}\nBalance: {}\n".format(player.health["HP"], player.stamina, player.fatigue, player.level, player.balance), inline=False)
        embed.add_field(name="Wounds", value=player.listWounds(), inline=True)
        embed.add_field(name="Equipment", value="Weapon: {}".format(player.weapon.name), inline=True)
        embed.add_field(name="Location", value="{}".format(self.locations[player.location]["description"]), inline=False)
        return embed

    def iteminfo(self, item):
        if not hasattr(item, "description"):
            item.description = "No description."
        weaponstats = ""
        defensestats = ""
        if item.type == "polearm" or item.type == "sword":
            item.bladed = True
        if item.bladed:
            weaponstats = "\n**Weapon Stats**\nBlade Weight: {} kg\nBlade Size: {} m\nPoint Sharpness: {}\nEdge Sharpness: {}".format(item.blade["mass"], item.blade["length"], item.blade["stab"]["sharpness"], item.blade["strike"]["sharpness"])
        description = "\n**Stats:**\nWeight: {} kg\nLength: {} m\nType: {}\nDescription: {}\n{}".format(item.mass, item.length, item.type, item.description, weaponstats, defensestats)
        embed = discord.Embed(title=item.name, description=description, color=0x000ed8)
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
        result = await fight.start()
        player1 = result[0]
        player2 = result[1]
        if player1.isDead():
            self.send_message(ctx.message.channel, "{} died.".format(player1.name))
        elif player2.isDead():
            self.send_message(ctx.message.channel, "{} died.".format(player2.name))
        else:
            self.send_message(ctx.message.channel, "The fight ended.")

    @commands.command(pass_context=True)
    async def fightai(self, ctx):
        player1 = await self.getPlayer(ctx.message.author.id, ctx)
        player2 = Player(self.defaultNPCinfo, isPlayer=False)
        player2.weapon = Item("steel_armingsword01", {"amount":1})
        fight = Fight(player1, player2, self, ctx.message.channel)
        result = await fight.start()
        player1 = result[0]
        player2 = result[1]
        if player1.isDead():
            self.send_message(ctx.message.channel, "{} died.".format(player1.name))
        elif player2.isDead():
            self.send_message(ctx.message.channel, "{} died.".format(player2.name))
        else:
            self.send_message(ctx.message.channel, "The fight ended.")

    @commands.command(pass_context=True)
    async def viewitem(self, ctx):
        itemname = ctx.message.content[10:]
        player = await self.getPlayer(ctx.message.author.id, ctx)
        matches = [item for item in player.inv if item.name.lower() == itemname.lower()] 
        print(itemname)
        if len(matches) > 0:
            await self.bot.send_message(ctx.message.channel, embed=self.iteminfo(matches[0]))
        else:
            await self.bot.send_message(ctx.message.channel, "You don't have that item.")
    @commands.command(pass_context=True)
    async def equip(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        print(ctx.message.content[7:])
        player.changeEquip(ctx.message.content[7:])
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