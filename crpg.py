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

body_part = fileIO("data/crpg/body_parts.json", "load")

def distance3D(pos1, pos2):
    x1 = pos1[0]
    y1 = pos1[1]
    z1 = pos1[2]
    x2 = pos2[0]
    y2 = pos2[1]
    z2 = pos2[2]
    d1 = math.sqrt((x2 - x1)*(x2 - x1)+(y2 - y1)*(y2 - y1))
    return math.sqrt(d1*d1+(z2 - z1)*(z2 - z1))

def uppercase(string):
    return string[0].upper()+string[1:]

class Player:
    def __init__(self, info, isPlayer=True):
        self.ai = AI(self)
        self.weapon = Item("fist", {"amount":2})
        self.isPlayer = isPlayer
        self.lastUpdate = time.time()
        self.bloodgain = 0.3
        for key in info:
            setattr(self, key, info[key])
        if not "stance" in info:
            self.stance = Stance(self, [0,0,1,1])
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
        self.combat_stats["reflex_speed"] = 1.5

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
            return True
        else:
            return False
        self.save()

    def applyDamage(self, wound):
        limb_damage_modifier = 6.8
        skull_strength = 10
        if wound == None:
            return
        if wound.type == "blunt":
            self.health[wound.location] -= wound.value
            if wound.loaction == "h":
                if wound.value > skull_strength:
                    self.health["h"] -= 65
        else:
            self.health[wound.location] -= wound.value[1]*wound.value[0]*limb_damage_modifier
            self.wounds.append(wound)
        self.save()

    def listWounds(self, numbered=False):
        content = ""
        i = 0
        marker = ""
        for x in self.wounds:
            if not hasattr(x, 'bleed'):
                x.bleed = 0
            if numbered:
                i += 1
                marker = str(i)+"."
            content += "{} {} on {}, bleeding at a rate of {}\n".format(marker, uppercase(x.type), body_part[x.location]["name"], round(x.bleed*100, 1))
        if content == "":
            content = "None"
        return content

    def bleedRate(self):
        s = 0
        for x in self.wounds:
            s += x.bleed
        s -= self.bloodgain
        return s

    def timeLeft(self):
        if self.bleedRate() <= 0:
            return "never."
        return "in "+str(round(self.health["HP"]/self.bleedRate(),1))+" seconds."

    def update(self):
        if not hasattr(self, "lastUpdate"):
            self.lastUpdate = time.time()
        self.health["HP"] += self.bloodgain
        for x in self.wounds:
            x.update()
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
            content += uppercase(key)+"\n"
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
        self.name = ""
        if self.x > 0:
            self.name += "Right, "
        elif self.x < 0:
            self.name += "Left, "
        else:
            self.name += "Center, "

        if self.y > 0:
            self.name += "high, "
        elif self.y < 0:
            self.name += "low, "
        else:
            self.name += "center, "

        if code[2] == 4:
            self.name += "overextended(!)"
        elif code[2] == 3:
            self.name += "forward"
        elif code[2] == 2:
            self.name += "midground"
        elif code[2] == 1:
            self.name += "close"

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
        print("type : "+self.type)
        self.stance = player.stance
        self.target = target
        dz = p_distance - self.stance.z
        dx = self.stance.x - body_part[target]["pos"][0]
        dy = self.stance.y - body_part[target]["pos"][1]
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
            if not "area" in weapon.blade["strike"]:
                self.attack_area = self.overlap
            else:
                self.attack_area = weapon.blade["strike"]["area"]
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
        print("buff {} speed {} lag {}".format(player.buffs["reaction"], player.combat_stats["reactionspeed"], limb_lag(player.health[attack.target])))
        self.destination = body_part[attack.target]["pos"]+[0]
        self.distance = distance3D([self.stance.x, self.stance.y, self.stance.z], self.destination)
        self.velocity = player.combat_stats["reflex_speed"]*weapon.balance/100

class Wound:
    def __init__(self, _type, location, value, text, pressure=None):
        self.type = _type
        self.value = value
        self.pressure = pressure
        self.location = location
        self.text = text
        self.bleed = 0
        self.bandaged = False
        self.lastUpdate = time.time()
        bloodloss_modifier = 0.2
        if self.type == "cut":
            self.bleed = self.value[0]*self.value[1]*bloodloss_modifier
        elif self.type == "stab":
            self.bleed = self.value[1]*bloodloss_modifier

    def severity(self):
        if self.type == "cut":
            if self.value[0] > 0.2 or self.value[1] > 0.1:
                return "severe"
        elif self.type == "stab":
            if self.value > 0.2:
                return "severe"
        return "mild"

    def bandage(self):
        self.bandaged = True
        self.bleed = self.bleed*0.01

    def update(self):
        heal_rate = 0.92
        if not hasattr(self, "lastUpdate"):
            self.lastUpdate = time.time()
        self.value[0] = self.value[0]*heal_rate*(time.time()-self.lastUpdate)
        self.value[1] = self.value[1]*heal_rate*(time.time()-self.lastUpdate)
        self.lastUpdate = time.time()

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
        self.logLength = 10
        self.status = "No action has been taken."

    def updatemsg(self):
        if len(self.turns) > 10:
            self.turns = self.turns[len(self.turns)-10:len(self.turns)-1]
        description = "you're in a fight, defend yourself m8"
        embed = discord.Embed(title="{} vs {}".format(self.p1.name, self.p2.name), description=description, color=0x16ff64)
        embed.add_field(name="Stances", value="{}'s stance: {}\n{}'s stance: {}\n\nDistance: {} m".format(self.p1.name, self.p1.stance.name, self.p2.name, self.p2.stance.name, self.distance), inline=False)
        
        if self.p1.isPlayer:
            h1 = self.p1.health    
            embed.add_field(name="{}'s Health".format(self.p1.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(round(h1["HP"], 2)), str(round(h1["h"], 2)), str(round(h1["t"], 2)), str(round(h1["la"], 2)), str(round(h1["ra"], 2)), str(round(h1["ll"], 2)), str(round(h1["rl"], 2))), inline=True)
            embed.add_field(name="{}'s Wounds".format(self.p1.name), value=self.p1.listWounds(), inline=True)
        #embed.add_field(name=" ",value=" ",inline=False)
        if not self.p2.isPlayer:
            h2 = self.p2.health
            embed.add_field(name="{}'s Health".format(self.p2.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(round(h2["HP"], 2)), str(round(h2["h"], 2)), str(round(h2["t"], 2)), str(round(h2["la"], 2)), str(round(h2["ra"], 2)), str(round(h2["ll"], 2)), str(round(h2["rl"], 2))), inline=True)
            embed.add_field(name="{}'s Wounds".format(self.p2.name), value=self.p2.listWounds(), inline=True)
        embed.add_field(name="Battle Log", value="\n".join(self.turns), inline=False)
        if self.p1.isPlayer:
            embed.add_field(name="{}'s Moves".format(self.p1.name), value=self.p1.weapon.getMoves(), inline=False)
        if self.p2.isPlayer:
            embed.add_field(name="{}'s Moves".format(self.p2.name), value=self.p2.weapon.getMoves(), inline=False)
        embed.add_field(name="Battle Status", value=self.status, inline=False)
        return embed

    async def start(self):
        self.message = await self.rpg.bot.send_message(self.channel, embed=self.updatemsg())
        return await self.nextTurn()

    async def resolveAttack(self, attack, defense, attacker, defender):
        def success(attack, defense):
            def_time = defense.distance/defense.velocity+defense.reaction
            atk_time = attack.distance/attack.velocity+defense.reaction  #super crude defense mechanic, to be reworked with stances later properly
            print("time to defend {} in stance {} from stance {} with distance {} is {} with limb delay of {}".format(attack.target, defense.stance.name, attack.stance.name, str(defense.distance), str(def_time), str(defense.reaction)))
            print("time to attack:"+str(atk_time)+" with velocity "+str(attack.velocity)+" and distance "+str(attack.distance))
            if atk_time > def_time:
                return False
            return True
        def calcDamage(attack, armour):
            if attack.overlap == 0:
                damage = Wound("blunt", attack.target, attack.weapon.mass-attack.weapon.blade["mass"], "{} hit {} with the handle of their weapon!".format(attacker.name, defender.name))
                attacker.stance = Stance(defender, body_part[attack.target]["pos"]+[4, 1])
                return damage
            if attack.overlap < 0:
                damage =  Wound("blunt", attack.target, 0, "{} was too far away to use their weapon!".format(attacker.name))
                return damage
            pressure = attack.weapon.blade[attack.type]["sharpness"]/100*attacker.strength["arm"]/attack.attack_area # sharpness applied as a multiplier of pressure, effectively dividing the impact area and thus increasing the imapct pressure
            if pressure > armour.cut_threshold:
                if attack.type == "strike":
                    cut_size = random.random()*body_part[attack.target]["size"]*armour.cut_resistance
                    cut_depth = random.random()*attack.energy*armour.cut_resistance
                    damage = Wound("cut", attack.target, [cut_size, cut_depth], "{} lands a cut on {}'s {}.".format(attacker.name, defender.name, body_part[attack.target]["name"]))
                else:
                    damage = Wound("stab", attack.target, [attack.weapon.blade["stab"]["area"], sigmoid(pressure*attack.momentum)*attack.weapon.blade["length"]], "{} successfully stabs {} in the {} with their {}.".format(attacker.name, defender.name, body_part[attack.target]["name"], attack.weapon.name))
            else:
                damage =  Wound("blunt", attack.target, 0, "{} couldn't pierce {}'s armour, but still dealt blunt damage to their {}.".format(attacker.name, defender.name, body))
            return damage
        if success(attack, defense):
            defender.stance = Stance(defender, body_part[attack.target]["pos"]+[1, 0])
            damage = calcDamage(attack, defender.armour[attack.target])
            text = damage.text
            defender.applyDamage(damage)
            defender.applyDamage(Wound("blunt", attack.target, attack.momentum, ""))
        else:
            text = "{} successfully blocked {}'s attack!".format(defender.name, attacker.name)
        return [attacker, defender, text]

    async def nextTurn(self):
        self.distance = abs(self.p1.pos)+abs(self.p2.pos)
        distance = self.distance
        if self.p1.isDead() or self.p2.isDead():
            return [self.p1,self.p2]
        if self.p1.isPlayer:
            self.status = "{}'s turn. They have 10 seconds to respond.".format(self.p1.name)
            await self.rpg.bot.edit_message(self.message, embed=self.updatemsg())
            action1 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p1.ID), self.channel)
            if not action1 == None:
                action1 = action1.split(" ")
                if not action1[0].lower() in self.p1.weapon.attacks and not action1[0] == "defend" and not action1[0] == "flee":
                    action1 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p1.ID), self.channel, "That's not a move you can do. You took no action this turn.")
                elif action1[0].lower() in self.p1.weapon.attacks:
                    action1 = [self.p1.weapon.attacks[action1[0].lower()]]+[action1[1]]
            else:
                action1 = ["defend", "t"]
        else:
            action1 = self.p1.ai.action(self)
            action2 = action2.split(" ")
            action1 = [action1[0].lower()]+[action1[1]]
        if self.p2.isPlayer:
            self.status = "{}'s turn. They have 10 seconds to respond.".format(self.p2.name)
            await self.rpg.bot.edit_message(self.message, embed=self.updatemsg())
            action2 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p2.ID), self.channel)
            if not action2 == None:
                action2 = action2.split(" ")
                if not action2[0].lower() in self.p2.weapon.attacks and action2[0] == "defend" and not action2[0] == "flee":
                    action2 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p2.ID), self.channel, "That's not a move you can do. You took no action this turn.")
                    action2 = ["defend", "t"]
                elif action2[0].lower() in self.p2.weapon.attacks:
                    action2 = [self.p2.weapon.attacks[action2[0].lower()]]+[action2[1]]
            else:
                action2 = ["defend","t"]
        else:
            action2 = self.p2.ai.action(self)
            action2 = action2.split(" ")
            action2 = [action2[0].lower()]+[action2[1]]
        if action1[0] == "defend":
            self.p1.buffs["reactionspeed"] = 0.7
        else:
            self.p1.buffs["reactionspeed"] = 1
        if action2[0] == "defend":
            self.p2.buffs["reactionspeed"] = 0.7
        else:
            self.p1.buffs["reactionspeed"] = 1
        attack1 = None
        attack2 = None
        if not action1[0] == "defend" and not action1[0] == "flee":
            attack1 = Attack(self.p1, distance, self.p1.weapon, action1[0], action1[1])
        if not action2[0] == "defend" and not not action2[0] == "flee":
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
        if action1 == ["flee"] or action2 == ["flee"]:
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
        self.startInv = [Item("fist", {"amount":2}), Item("clean_bandage", {"amount":5}), Item("waterskin", {"amount":1}), Item("bread_chunk", {"amount":10})]
        self.materials = [Material("mild_steel", True, 70, 370, 8050)]
        self.defaultNPCinfo = fileIO("data/crpg/default_npc.json", "load")
        self.defaultNPCinfo["weapon"] = (Item("steel_axe01", {"amount":1}))
        self.bp_names = {
            "head":"h",
            "torso":"t",
            "left arm":"la",
            "right arm":"ra",
            "left leg":"ll",
            "right leg":"rl"
        }
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
                return inv
        inv.append(item)
        return inv

    async def removeItem(self, inv, item):
        for x in inv:
            if x.id == item.id:
                x.amount -= 1
                if x.amount <= 0:
                    del(x)
                    return inv
        return inv

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

    async def promptUser(self, author, channel, prompt=None, embed=None, timelimit=None):
        if not prompt == None:
            await self.bot.send_message(channel, prompt, embed=embed)
        elif not embed == None:
            await self.bot.send_message(channel, embed=embed)
        response = await self.bot.wait_for_message(timeout=timelimit, author=author, channel=channel)
        if response == None:
            return None
        return response.content

    async def newFight(self, p1, p2, ctx):
        return Fight(p1, p2, self, ctx.message.channel)

    def listItems(self, inv, numbered=False, Filter=None):
        content = ""
        i = 0
        marker = ""
        for item in inv:
            if numbered:
                i += 1
                marker = str(i)+"."
            content += "\n{} {} x {}".format(marker, item.name, item.amount)
        return content

    def listStats(self, player):
        content = "Health: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n"

    def statusEmbed(self, player):
        embed = discord.Embed(title="{}'s Status".format(player.name), color=0x16ff64)
        if player.isDead():
            embed.add_field(name="You are dead!", value="You can't do much now that you're not alive.", inline=False)
        embed.add_field(name="Stats", value="Health: {}\nStamina: {}\nFatigue: {}\nLevel: {}\nBalance: {}\n".format(player.health["HP"], player.stamina, player.fatigue, player.level, player.balance), inline=False)
        embed.add_field(name="Wounds", value="At this rate, you will bleed out {}\n".format(player.timeLeft())+player.listWounds(), inline=True)
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
        description = "\n**Stats:**\nWeight: {} kg\nLength: {} m\nType: {}\nDescription: {}\n{}".format(item.mass, item.length, uppercase(item.type), item.description, weaponstats, defensestats)
        embed = discord.Embed(title=item.name, description=description, color=0x000ed8)
        return embed

    @commands.command(pass_context=True)
    async def inventory(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        embed = discord.Embed(title="Inventory\n"+str(round(player.invmass(), 2))+" kg", description=self.listItems(player.inv), color=0x16ffeb)
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
            await self.bot.send_message(ctx.message.channel, "{} died.".format(player1.name))
        elif player2.isDead():
            await self.bot.send_message(ctx.message.channel, "{} died.".format(player2.name))
        else:
            await self.bot.send_message(ctx.message.channel, "The fight ended.")
        player1.save()
        player2.save()

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
            await self.bot.send_message(ctx.message.channel, "{} died.".format(player1.name))
        elif player2.isDead():
            await self.bot.send_message(ctx.message.channel, "{} died.".format(player2.name))
        else:
            await self.bot.send_message(ctx.message.channel, "The fight ended.")
        player1.save()
        player2.save()

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
        if ctx.message.content.split(" ")[1] == "weapon":
            success = player.changeEquip(ctx.message.content[7:])
            if success:
                await self.bot.send_message(ctx.message.channel, embed=discord.Embed(title="Success", description="Set your weapon to {}.".format(player.weapon.name), color=0x16ffeb))
            else:
                await self.bot.send_message(ctx.message.channel, embed=discord.Embed(title="Failed to Equip", description="You don't have {}.".format(player.weapon.name), color=0x16ffeb))
        elif ctx.message.content.split(" ")[1] == "armour" or ctx.message.content.split(" ")[1] == "armor":
            inv = [i for i in player.inv if hasattr(i, "wearable") and i.wearable]
            embed = discord.Embed(title="Available Armour Pieces:", decription="What piece of armour would you like to equip?\n"+self.listItems(inv), color=0xffc414)
            selection = await self.promptUser(ctx.message.author, ctx.message.channel, embed=embed)
        player.save()

    @commands.command(pass_context=True)
    async def save(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        player.save()

    @commands.command(pass_context=True)
    async def bandage(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        inv = [i for i in player.inv if hasattr(i, "becomes") and "bandage" in i.becomes]
        embed = discord.Embed(title="Available Bandages:\n__Select one.__", description=self.listItems(inv, numbered=True), color=0x16ffeb)
        selection1 = await self.promptUser(ctx.message.author, ctx.message.channel, embed=embed)
        if not selection1.isdigit():
            return await self.bot.send_message(ctx.message.channel, "Cancelled bandaging.")
        embed = discord.Embed(title="Current Wounds:\n__Select one.__", description=player.listWounds(numbered=True), color=0x16ffeb)
        selection2 = await self.promptUser(ctx.message.author, ctx.message.channel, embed=embed)
        if not selection2.isdigit():
            return await self.bot.send_message(ctx.message.channel, "Cancelled bandaging.")
        selection1 = int(selection1) - 1
        selection2 = int(selection2) - 1
        player.wounds[selection2].bandage()
        await self.removeItem(player.inv, inv[selection1].id)
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
        player.save()

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