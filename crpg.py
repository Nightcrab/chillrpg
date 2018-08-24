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
import collections
import asyncio

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
default_player = fileIO("data/crpg/default_player.json", "load")

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
        for key in info:
            setattr(self, key, info[key])
        if not "stance" in info:
            self.stance = Stance(self, [0,0,1,1,90,90])
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
        if self.health["t"] <= 0:
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
            content += "{} {} on {}, bleeding at a rate of {} HP/minute\n".format(marker, uppercase(x.type), body_part[x.location]["name"], round(x.bleed*60, 1))
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

    def balance(self, mode="int"):
        for x in self.inv:
            if x.itemID == "coin":
                if mode == "str":
                    return str(x.amount)+" coins"
                return x.amount
        if mode == "str":
            return "No coins"
        return 0

    def update(self):
        for key in default_player:
            if not hasattr(self, key):
                setattr(self, key, default_player[key])
            if isinstance(default_player[key], collections.Mapping):
                for k in default_player[key]:
                    if not default_player[key][k] in getattr(self, key):
                        d = getattr(self, key)
                        d[k] = default_player[key][k]

        if not hasattr(self, "lastUpdate"):
            self.lastUpdate = time.time()
        self.health["HP"] += self.bloodgain
        for x in self.wounds:
            x.update()
            if hasattr(x, "healed") and x.healed:
                self.wounds.remove(x)
            if x.bleed > 0:
                self.health["HP"] -= x.bleed * (time.time() - self.lastUpdate)
        for x in self.health:
            if self.health[x] > 100:
                self.health[x] = 100
            if self.health[x] < 0:
                self.health[x] = 0
            if x == "HP" or x == "bleed":
                continue
            self.health[x] += body_part[x]["healrate"] * (time.time() - self.lastUpdate)
        self.lastUpdate = time.time()
        self.save()

    def invmass(self):
        s = 0
        for x in self.inv:
            s += x.mass*x.amount
        return s

    def save(self):
        if not self.isPlayer:
            if not os.path.exists("data/crpg/npcs/{}".format(self.ID)):
                os.makedirs("data/crpg/npcs/{}".format(self.ID))
            savePickle("data/crpg/npcs/{}/info.obj".format(self.ID), self)
        else:
            if not os.path.exists("data/crpg/players/{}".format(self.ID)):
                os.makedirs("data/crpg/players/{}".format(self.ID))
            savePickle("data/crpg/players/{}/info.obj".format(self.ID), self)

class Item:
    def __init__(self, itemID, *info, **kwargs):

        #if id is given, take the properties of default item with that id, if not, properties should be passed in a dictionary
        self.amount = 1
        if itemID == "":
            self.itemID = genID()
        else:
            self.itemID = itemID
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
        self.rotx = code[3]
        self.rotz = code[4]
        self.line = code[6]
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
    def __init__(self, name, cut_threshold, cut_resistance, brittle, tensile, toughness, density):
        self.name = name
        self.brittle = brittle
        self.tensile = tensile
        self.toughness = toughness
        self.density = density
        self.cut_resistance = cut_resistance
        self.cut_threshold = cut_threshold

class Attack:
    """An attack, usually countered with a defense."""
    def __init__(self, player, p_distance, weapon, atktype, target):
        self.type = atktype
        print("type : "+self.type)
        self.stance = player.stance
        self.target = target
        self.angle = random.choice([180, 0, 90, 270]) #left, right, up and down; left as in from the left, not to the left
        self.destination = body_part[target]["pos"]+[player.proportions["arm"]]+[self.angle]+[player.stance.rotz]
        dz = self.destination[2] - self.stance.z
        dx = self.stance.x - self.destination[0]
        dy = self.stance.y - self.destination[1]
        d1 = math.sqrt(dx*dx+dy*dy)
        self.distance = math.sqrt(dz*dz+d1*d1)
        self.weapon = weapon

        com_dist = self.weapon.length*self.weapon.balance
        self.rot_speed = 
        w_overlap = self.weapon.length - self.distance
        if self.weapon.blade["length"] > w_overlap:
            self.overlap = w_overlap
        else:
            self.overlap = self.weapon.blade["length"]
        if atktype == "stab":
            w_acceleration = player.strength["arm"]/weapon.mass
            b_acceleration = player.strength["legs"]/(player.mass+player.invmass()+weapon.mass)
            self.velocity = math.sqrt(2*w_acceleration*(self.distance+self.stance.lungelen()))
            self.weapon_velocity = self.velocity
            self.acceleration = w_acceleration + b_acceleration
            self.attack_area = weapon.blade["stab"]["area"]
        
        if atktype == "strike":
            self.acceleration = player.strength["arm"]/weapon.mass
            self.velocity = math.sqrt(2*self.acceleration*self.distance)
            self.weapon_velocity = self.velocity
            if not "area" in weapon.blade["strike"]:
                self.attack_area = self.overlap
            else:
                self.attack_area = weapon.blade["strike"]["area"]
        self.energy = 1/2*self.weapon.blade["mass"]*self.velocity*self.velocity
        self.momentum = self.weapon.blade["mass"]*self.velocity
        self.time = 2*self.distance/self.velocity

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
        xrot = attack.destination[]
        self.destination = body_part[attack.target]["pos"]+self.player.proportions["arm"]/4+[xrot, zrot]
        self.distance = distance3D([self.stance.x, self.stance.y, self.stance.z], self.destination)
        

class Wound:
    def __init__(self, _type, location, value, text, pressure=None):
        self.type = _type
        self.value = value
        if not pressure == None:
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
        if self.bleed == 0:
            self.healed = True
            return "healed"
        return "severe"
        if 0 < self.bleed <= 1:
            return "minor"
        if 1 < self.bleed <= 2:
            return "mild"
        if 2 < self.bleed <= 5:
            return "moderately severe"
        if 5 < self.bleed <= 15:
            return "severe"
        if 15 < self.bleed <= 50:
            return "fatal"
        if 50 < self.bleed:
            return "all of your blood vessels were destroyed by this"

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
        self.p1.pos = -0.4
        self.p2.pos = 0.4
        self.normal_moves = ["defend", "flee", "move"]
        self.distance = abs(self.p1.pos)+abs(self.p2.pos)
        self.rpg = chillrpg
        self.channel = channel
        self.turns = ["The battle began between {} and {}.".format(self.p1.name, self.p2.name)]
        self.logLength = 10
        self.status = "No action has been taken."
        self.names = {
            "head":"h",
            "leftarm":"la",
            "rightarm":"ra",
            "leftleg":"ll",
            "rightleg":"rl",
            "torso":"t"
        }

    def updatemsg(self):
        if len(self.turns) > 10:
            self.turns = self.turns[len(self.turns)-10:len(self.turns)-1]
        description = "you're in a fight, defend yourself m8"
        embed = discord.Embed(title="{} vs {}".format(self.p1.name, self.p2.name), description=description, color=0x16ff64)
        embed.add_field(name="Stances", value="{}'s stance: {}\n{}'s stance: {}\n\nDistance: {} m".format(self.p1.name, self.p1.stance.name, self.p2.name, self.p2.stance.name, self.distance), inline=False)
        
        #if self.p1.isPlayer:
        h1 = self.p1.health    
        embed.add_field(name="{}'s Health".format(self.p1.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(round(h1["HP"], 2)), str(round(h1["h"], 2)), str(round(h1["t"], 2)), str(round(h1["la"], 2)), str(round(h1["ra"], 2)), str(round(h1["ll"], 2)), str(round(h1["rl"], 2))), inline=True)
        embed.add_field(name="{}'s Wounds".format(self.p1.name), value=self.p1.listWounds(), inline=True)
        embed.add_field(name="----",value="----",inline=False)
        #if self.p2.isPlayer:
        h2 = self.p2.health
        embed.add_field(name="{}'s Health".format(self.p2.name), value="HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(round(h2["HP"], 2)), str(round(h2["h"], 2)), str(round(h2["t"], 2)), str(round(h2["la"], 2)), str(round(h2["ra"], 2)), str(round(h2["ll"], 2)), str(round(h2["rl"], 2))), inline=True)
        embed.add_field(name="{}'s Wounds".format(self.p2.name), value=self.p2.listWounds(), inline=True)
        embed.add_field(name="Battle Log", value="\n".join(self.turns), inline=False)
        if self.p1.isPlayer:
            embed.add_field(name="{}'s Moves".format(self.p1.name), value=self.p1.weapon.getMoves()+self.rpg.listArr(self.normal_moves, upper=True), inline=False)
        if self.p2.isPlayer:
            embed.add_field(name="{}'s Moves".format(self.p2.name), value=self.p2.weapon.getMoves()+self.rpg.listArr(self.normal_moves, upper=True), inline=False)
        embed.add_field(name="Battle Status", value=self.status, inline=False)
        embed.set_footer(text="Send the name of the move you would like to make and a target, e.g 'slice leftarm'")
        return embed

    async def start(self):
        self.p1.update()
        self.p2.update()
        self.message = await self.rpg.bot.send_message(self.channel, embed=self.updatemsg())
        return await self.nextTurn()

    async def resolveAttack(self, attack, defense, attacker, defender):
        def success(attack, defense):
            atk_rot_time_x = attack.destination[3]/attack.rotspeed
            atk_rot_time_z = attack.destination[4]/attack.rotspeed
            atk_move_time = attack.time
            atk_rot_time = max(atk_rot_time_z, atk_rot_time_x)
            atk_time = atk_move_time + atk_rot_time
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
            pressure = attack.weapon.blade[attack.type]["sharpness"]/100*attacker.strength["arm"]/attack.attack_area # sharpness applied as a multiplier, effectively dividing the impact area and thus increasing the imapct pressure
            print("pressure: "+str(pressure))
            if pressure > armour.cut_threshold:
                if attack.type == "strike":
                    cut_size = random.random()*body_part[attack.target]["size"]*armour.cut_resistance
                    cut_depth = random.random()*attack.energy*armour.cut_resistance
                    damage = Wound("cut", attack.target, [cut_size, cut_depth], "{} lands a cut on {}'s {}.".format(attacker.name, defender.name, body_part[attack.target]["name"]), pressure=pressure)
                else:
                    damage = Wound("stab", attack.target, [attack.weapon.blade["stab"]["area"], sigmoid(pressure*attack.momentum)*attack.overlap], "{} successfully stabs {} in the {} with their {}.".format(attacker.name, defender.name, body_part[attack.target]["name"], attack.weapon.name), pressure=pressure)
            else:
                damage =  Wound("blunt", attack.target, 0, "{} dealt blunt damage to {}'s {}.".format(attacker.name, defender.name, body_part[attack.target]["name"]), pressure=pressure)
            return damage
        if success(attack, defense):
            skull_strength = 10
            defender.stance = Stance(defender, body_part[attack.target]["pos"]+[1, 0])
            damage = calcDamage(attack, defender.armour[attack.target])
            text = damage.text
            defender.applyDamage(damage)
            if hasattr(damage, "pressure") and damage.pressure > skull_strength and damage.location == "h":
                text += "\n{}'s skull was broken!".format(defender.name)
                self.p2.health["HP"] = 0
            defender.applyDamage(Wound("blunt", attack.target, attack.momentum, ""))
        else:
            text = "{} successfully blocked {}'s attack!".format(defender.name, attacker.name)
        return [attacker, defender, text]

    async def nextTurn(self):
        self.distance = abs(self.p1.pos)+abs(self.p2.pos)
        self.p1.range = self.p1.stance.z+math.cos(math.radians(self.p1.stance.rotx))*self.p1.weapon.length
        self.p2.range = self.p2.stance.z+math.cos(math.radians(self.p2.stance.rotx))*self.p2.weapon.length
        if self.p1.isDead() or self.p2.isDead():
            return [self.p1,self.p2]
        if self.p1.isPlayer:
            self.status = "{}'s turn. They have 5 seconds to respond.".format(self.p1.name)
            await self.rpg.bot.edit_message(self.message, embed=self.updatemsg())
            action1 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p1.ID), self.channel, timelimit=5)
            if not action1 == None:
                action1 = action1.split(" ")
                if not action1[0].lower() in self.p1.weapon.attacks and not action1[0].lower() in self.normal_moves or not action1[1].lower() in self.names:
                    await self.rpg.bot.send_message(self.channel, "That's not a valid move. You defended this turn.")
                    action1 = ["defend", "t"]
                elif action1[0].lower() in self.p1.weapon.attacks:
                    action1 = [self.p1.weapon.attacks[action1[0].lower()]]+[action1[1]]
                elif action1[0].lower() == "move":
                    if len(action1) < 3:
                        await self.rpg.bot.send_message(self.channel, "Not enough parameters specified. (requires direction and distance)")
                    elif not action1[1].lower() == "forward" and not action1[1].lower() == "back":
                        await self.rpg.bot.send_message(self.channel, "Direction must be forward or back.")
                    elif not action1[2].isdigit():
                        await self.rpg.bot.send_message(self.channel, "Distance must be a number, in centimeters.")
                    elif int(action1[2]) <= 0:
                        await self.rpg.bot.send_message(self.channel, "Distance can't be 0 or negative.")
                    else:
                        if int(action1[2]) > 100:
                            action1[2] = "100"
                        if action1[1].lower() == "forward":
                            self.p1.pos += int(action1[2])/100
                        else:
                            self.p1.pos -= int(action1[2])/100
            else:
                msg = await self.rpg.bot.send_message(self.channel, "{} timed out.".format(self.p1.name))
                await self.rpg.deletemsg(msg, 2000)
                action1 = ["defend", "t"]
        else:
            action1 = self.p1.ai.action(self)
            action2 = action2.split(" ")
            action1 = [action1[0].lower()]+[action1[1]]
        if self.p2.isPlayer:
            self.status = "{}'s turn. They have 10 seconds to respond.".format(self.p2.name)
            await self.rpg.bot.edit_message(self.message, embed=self.updatemsg())
            action2 = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.p2.ID), self.channel, timelimit=10)
            if not action2 == None:
                action2 = action2.split(" ")
                if not action2[0].lower() in self.p2.weapon.attacks and not action2[0].lower() in self.normal_moves or not action2[1].lower() in self.names:
                    await self.rpg.bot.send_message(self.channel, "That's not a valid move. You defended this turn.")
                    action2 = ["defend", "t"]
                elif action2[0].lower() in self.p2.weapon.attacks:
                    action2 = [self.p2.weapon.attacks[action2[0].lower()]]+[action2[1]]
                elif action2[0].lower() == "move":
                    if len(action2) < 3:
                        await self.rpg.bot.send_message(self.channel, "Not enough parameters specified. (requires direction and distance)")
                    elif not action2[1].lower() == "forward" and not action2[1].lower() == "back":
                        await self.rpg.bot.send_message(self.channel, "Direction must be forward or back.")
                    elif not action2[2].isdigit():
                        await self.rpg.bot.send_message(self.channel, "Distance must be a number, in centimeters.")
                    elif int(action2[2]) <= 0:
                        await self.rpg.bot.send_message(self.channel, "Distance can't be 0 or negative.")
                    else:
                        if int(action2[2]) > 100:
                            action2[2] = "100"
                        if action2[1].lower() == "forward":
                            self.p2.pos += int(action2[2])/100
                        else:
                            self.p2.pos -= int(action2[2])/100
            else:
                msg = await self.rpg.bot.send_message(self.channel, "{} timed out.".format(self.p2.name))
                await self.rpg.deletemsg(msg, 2)
                action2 = ["defend","t"]
        else:
            action2 = self.p2.ai.action(self)
            action2 = action2.split(" ")
            action2 = [action2[0].lower()]+[action2[1]]
        if action1[0] == "defend":
            self.p1.buffs["reactionspeed"] = 0.5
        else:
            self.p1.buffs["reactionspeed"] = 1
        if action2[0] == "defend":
            self.p2.buffs["reactionspeed"] = 0.5
        else:
            self.p1.buffs["reactionspeed"] = 1
        attack1 = None
        attack2 = None
        self.distance = abs(self.p1.pos)+abs(self.p2.pos)
        if self.distance <= 0:
            self.turns.append("{} and {} collided!".format(self.p1.name, self.p2.name))
            self.p1.pos -= abs(self.distance)/2+0.3
            self.p2.pos += abs(self.distance)/2+0.3
        self.distance = abs(self.p1.pos)+abs(self.p2.pos)
        if not action1[0].lower() in self.normal_moves:
            attack1 = Attack(self.p1, self.distance, self.p1.weapon, action1[0], action1[1])
        if not action2[0].lower() in self.normal_moves:
            attack2 = Attack(self.p2, self.distance, self.p2.weapon, action2[0], action2[1])
        if not attack1 == None and not self.p1.isDead():
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
        
class Conversation:
    def __init__(self, rpg, channel, p1, p2):
        self.rpg = rpg
        self.p1 = p1
        self.p2 = p2
        self.channel = channel
        self.talker = p2
        self.listener = p1
        self.currentDialogue = "..."
        self.options = ["Hello.", "Goodbye."]
        self.state = "dialogue"
        self.modules = []
        self.over = False
        self.firstTurn = True

    def updatemsg(self):
        embed = discord.Embed(title="Conversation between {} and {}\n\n{}:".format(self.p1.name, self.p2.name, self.talker.name), description="\""+self.currentDialogue+"\"", color=0x0263ff)
        if self.state == "dialogue":
            embed.add_field(name="Options", value=self.rpg.listArr(self.options, numbered=True))
        if self.state == "shop":
            selling1 = self.p1.selling
            selling2 = self.p2.selling
            selling1 = self.rpg.listItems(list(filter(lambda i: i.itemID in selling1, self.p1.inv)))
            selling2 = self.rpg.listItems(list(filter(lambda i: i.itemID in selling2, self.p2.inv)))
            if selling1 == "":
                selling1 = "No items."
            if selling2 == "":
                selling2 = "No items."
            buying1 = self.rpg.listArr({k: items[k]["name"]+" for "+str(v)+" coins each" for k, v in self.p1.buying.items()}.values())
            buying2 = self.rpg.listArr({k: items[k]["name"]+" for "+str(v)+" coins each" for k, v in self.p2.buying.items()}.values())
            if buying1 == "":
                buying1 = "No items."
            if buying2 == "":
                buying2 = "No items."
            embed.add_field(name="{}'s balance:".format(self.p1.name), value=self.p1.balance(mode="str"), inline=True)
            embed.add_field(name="{}'s balance:".format(self.p2.name), value=self.p2.balance(mode="str"), inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
            embed.add_field(name="What {} has to offer:".format(self.p1.name), value=selling1, inline=True)
            embed.add_field(name="What {} has to offer:".format(self.p2.name), value=selling2, inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
            embed.add_field(name="What {} wants to buy:".format(self.p1.name), value=buying1, inline=True)
            embed.add_field(name="What {} wants to buy:".format(self.p2.name), value=buying2, inline=True)
            embed.add_field(name="Options", value="Type \"nevermind\" to cancel the trade.\nTo sell something, type sell (amount) (item name).\nTo sell something, type buy (amount) (item name).", inline=False)
        return embed
    async def processDialogue(self):
        if self.currentDialogue.lower().startswith("goodbye"):
            self.over = True
            return
        if self.currentDialogue.lower().startswith("i'd like to buy") or self.currentDialogue.lower().startswith("i'd like to sell"):
            self.talker, self.listener = self.listener, self.talker
            self.state = "shop"
            return
        if self.listener.isPlayer:
            choice = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.listener.ID), self.channel, prompt=None, returncontent=False)
            if not self.firstTurn:
                await self.rpg.bot.delete_message(choice)
            choice = choice.content
            if not choice.isdigit():
                await self.rpg.bot.send_message(ctx.message.channel, "Invalid selection. Cancelled dialogue.")
            if int(choice) > len(self.options):
                await self.rpg.bot.send_message(ctx.message.channel, "Invalid selection. Cancelled dialogue.")
            self.currentDialogue = self.options[int(choice) - 1]
            self.options = ["Continue."]
        else:
            confirm = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.talker.ID), self.channel, prompt=None, returncontent=False)
            if not self.firstTurn:
                await self.rpg.bot.delete_message(confirm)
            if self.currentDialogue in self.listener.dialogue["options"]:
                self.options = [uppercase(o) for o in self.listener.dialogue["options"][self.currentDialogue]]+["Goodbye."]
            else:
                self.options = ["I'd like to buy something.", "I'd like to sell something.", "Goodbye."]+self.listener.dialogue["options"]["default"]
            self.currentDialogue = self.listener.dialogue["responses"][self.currentDialogue]
        self.talker, self.listener = self.listener, self.talker

    async def processShop(self):
        self.currentDialogue = "Let's see what you got."
        choice = await self.rpg.promptUser(await self.rpg.bot.get_user_info(self.listener.ID), self.channel, prompt=None)
        if choice.lower().startswith("nevermind"):
            self.state = "dialogue"
            self.currentDialogue = "..."
            self.options = ["Goodbye"]
            if "default" in self.talker.dialogue["options"]:
                self.options = self.options + self.talker.dialogue["options"]["default"]
            return
        if choice.lower().startswith("sell"):
            amount = choice.split(" ")[1]
            if not amount.isdigit() or int(amount) < 1:
                return await self.rpg.bot.send_message(self.channel, "That's not a valid amount.")
            itemname = " ".join(choice.split(" ")[2:])
            for index, item in enumerate(self.listener.inv):
                if item.name.lower() == itemname.lower():
                    if item.amount < int(amount):
                        return await self.rpg.bot.send_message(self.channel, "You don't have enough items for that.")
                    if self.talker.isPlayer:
                        return await self.rpg.bot.send_message(self.channel, "This player isn't buying any items.")
                    if not item.itemID in self.talker.buying:
                        return await self.rpg.bot.send_message(self.channel, "This player isn't interested in that.")
                    if self.talker.balance() < self.talker.buying[item.itemID]*int(amount):
                        return await self.rpg.bot.send_message(self.channel, "{} can't afford that much.".format(self.talker.name))
                    await self.rpg.removeItem(self.talker.inv, Item("coin"), amount=self.talker.buying[item.itemID]*int(amount))
                    await self.rpg.addItem(self.talker.inv, item, amount=int(amount))
                    await self.rpg.addItem(self.listener.inv, Item('coin'), amount=self.talker.buying[item.itemID]*int(amount))
                    await self.rpg.removeItem(self.listener.inv, item, amount=int(amount))
                    return await self.rpg.bot.send_message(self.channel, "{} sold {} {} to {}.".format(self.listener.name, amount, uppercase(itemname), self.talker.name))
            return await self.rpg.bot.send_message(self.channel, "You don't have that item.")
        if choice.lower().startswith("buy"):
            amount = choice.split(" ")[1]
            if not amount.isdigit() or int(amount) < 1:
                return await self.rpg.bot.send_message(self.channel, "That's not a valid amount.")
            itemname = " ".join(choice.split(" ")[2:])
            for x in items:
                if items[x]["name"] == itemname.lower():
                    itemname = x
                    break
            if self.talker.isPlayer:
                return await self.rpg.bot.send_message(self.channel, "This player isn't selling any items.")
            if not itemname in self.talker.selling:
                return await self.rpg.bot.send_message(self.channel, "This player isn't selling that item.")
            if self.listener.balance() < self.talker.selling[itemname]*int(amount):
                return await self.rpg.bot.send_message(self.channel, "{} can't afford that much.".format(self.listener.name))
            for index, item in enumerate(self.talker.inv):
                if item.name.lower() == itemname.lower():
                    if item.amount < int(amount):
                        return await self.rpg.bot.send_message(self.channel, "{} doesn't have enough items for that.".format(self.talker.name))
                    await self.rpg.removeItem(self.listener.inv, Item("coin"), amount=self.listener.selling[item.itemID]*int(amount))
                    await self.rpg.addItem(self.talker.inv, Item("coin"), amount=self.listener.selling[item.itemID]*int(amount))
                    await self.rpg.addItem(self.listener.inv, item, amount=int(amount))
                    await self.rpg.removeItem(self.talker.inv, item, amount=int(amount))
                    return await self.rpg.bot.send_message(self.channel, "{} sold {} {} to {}.".format(self.talker.name, amount, uppercase(itemname), self.listener.name))
            return await self.rpg.bot.send_message(self.channel, "{} doesn't have that item.".format(self.talker.name))

    async def start(self):
        self.message = await self.rpg.bot.send_message(self.channel, embed=self.updatemsg())
        return await self.nextTurn()
    async def nextTurn(self):
        if self.state == "dialogue":
            await self.processDialogue()
        if self.state == "shop":
            await self.processShop()
        self.firstTurn = False
        if self.p1.name == self.listener.name:
            self.p1 = self.listener
            self.p2 = self.talker
        else:
            self.p2 = self.listener
            self.p1 = self.talker
        self.p1.update()
        self.p2.update()
        await self.rpg.bot.edit_message(self.message, embed=self.updatemsg())
        if self.over:
            await self.rpg.bot.send_message(self.channel, "Ended conversation.")
            return [self.p1, self.p2]
        return await self.nextTurn()

class ChillRPG:
    """Class holding game information, methods and player interaction."""
    def __init__(self, bot):
        self.bot = bot
        self.yes = ["yes", "y", "ok", "okay", "yep", "yeah"]
        self.locations = read_folder("locations") #dictionary of all json files in data/crpg/locations/
        self.no = ["no", "n"]
        self.startkits = [[Item("pitchfork01", {"amount":1})],
                          [Item("steel_axe01", {"amount":1}), Item("timber01", {"amount":100})],
                          [Item("steel_spear01", {"amount":1})],
                          [Item("steel_armingsword01", {"amount":1})],
                          [Item("steel_armingsword01", {"amount":1}),Item("steel_mace01", {"amount":1})]]
        self.startInv = [Item("fist", {"amount":2}), Item("clean_bandage", {"amount":5}), Item("waterskin", {"amount":1}), Item("bread_chunk", {"amount":10})]
        self.materials = [Material("mild_steel", 4, 5, True, 70, 370, 8050)]
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
        self.players = {**read_folder('npcs', filetype="obj"), **read_folder('players', filetype="obj")}
        ginger = fileIO("data/crpg/ginger.json", "load")
        ginger = Player(ginger, isPlayer=False)
        self.players[ginger.ID] = ginger
        ginger.inv = [Item("bread_chunk", {"amount":250}), Item("clean_bandage", {"amount":750}), Item("coin", {"amount":20000})]
        ginger.save()
        print(ginger.name)
        for x in self.players:
            location = self.locations[self.players[x].location]
            location["players"].append(self.players[x].ID)
        print(self.locations["chillbar"]["players"])

    def refreshInv(self, inv):
        for x in inv.length:
            if x.amount == 0:
                del x

    def unloadPlayer(self, ID):
        if not ID in self.players:
            return
        del(self.players[ID])

    async def addItem(self, inv, item, amount=1):
        for x in inv:
            if x.itemID == item.itemID:
                x.amount += amount
                return inv
        inv.append(item)
        return inv

    async def removeItem(self, inv, item, amount=1):
        print(item.itemID)
        for x in inv:
            if x.itemID == item.itemID:
                x.amount -= amount
                if x.amount <= 0:
                    inv.remove(x)
        return inv

    async def getPlayer(self, ID, ctx, someone_else=False): #Get a user's character, if it exists
        if ID in self.players:
            self.players[ID].update()
            if not ID in self.locations[self.players[ID].location]["players"]:
                self.locations[self.players[ID].location]["players"].append(ID)
            return self.players[ID]
        if os.path.exists("data/crpg/players/{}".format(ID)):
            self.players[ID] = loadPickle("data/crpg/players/{}/info.obj".format(ID))
            if not ID in self.locations[self.players[ID].location]["players"]:
                self.locations[self.players[ID].location]["players"].append(ID)
            self.players[ID].update()
            return self.players[ID]
        else:
            if someone_else:
                return None
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

    async def promptUser(self, author, channel, prompt=None, embed=None, timelimit=None, returncontent=True):
        if not prompt == None:
            await self.bot.send_message(channel, prompt, embed=embed)
        elif not embed == None:
            await self.bot.send_message(channel, embed=embed)
        response = await self.bot.wait_for_message(timeout=timelimit, author=author, channel=channel)
        if response == None:
            return None
        if returncontent:
            return response.content
        return response

    async def newFight(self, p1, p2, ctx):
        return Fight(p1, p2, self, ctx.message.channel)

    async def deletemsg(self, message, delay):
        asyncio.sleep(delay)
        return await self.bot.delete_message(message)

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

    def listLocations(self):
        content = ""
        for k in self.locations:
            content += "\n**{}** : {}".format(self.locations[k]["name"], self.locations[k]["description"])
        return content

    def getPlayerSync(self, ID, someone_else=False): #Get a user's character, if it exists
        if ID in self.players:
            self.players[ID].update()
            if not ID in self.locations[self.players[ID].location]["players"]:
                self.locations[self.players[ID].location]["players"].append(ID)
            return self.players[ID]
        else:
            return None

    def listHealth(self, player):
        h1 = player.health
        return "HP: {}\nHead: {}\nTorso: {}\nLeft Arm: {}\nRight Arm: {}\nLeft Leg: {}\nRight Leg: {}\n".format(str(round(h1["HP"], 2)), str(round(h1["h"], 2)), str(round(h1["t"], 2)), str(round(h1["la"], 2)), str(round(h1["ra"], 2)), str(round(h1["ll"], 2)), str(round(h1["rl"], 2)))

    def statusEmbed(self, player):
        player.update()
        embed = discord.Embed(title="{}'s Status".format(player.name), color=0x16ff64)
        if player.isDead():
            embed.add_field(name="You are dead!", value="You can't do much now that you're not alive.", inline=False)
        embed.add_field(name="Health", value=self.listHealth(player), inline=False)
        embed.add_field(name="Stats", value="Stamina: {}\nFatigue: {}\nLevel: {}\nBalance: {}\n".format(player.stamina, player.fatigue, player.level, player.balance()), inline=False)
        embed.add_field(name="Wounds", value="At this rate, you will bleed out {}\n".format(player.timeLeft())+player.listWounds(), inline=True)
        embed.add_field(name="Equipment", value="Weapon: {}".format(player.weapon.name), inline=True)
        embed.add_field(name="Location\n"+self.locations[player.location]["name"], value="{}".format(self.locations[player.location]["description"]), inline=False)
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

    async def listPlayers(self, ctx, location):
        content = ""
        for x in location["players"]:
            player = await self.getPlayer(x, ctx)
            content += "{}\n".format(player.name)
        return content

    def listArr(self, arr, numbered=False, upper=False):
        content = ""
        i = 0
        marker = ""
        for x in arr:
            if numbered:
                i += 1
                marker = str(i)+". "
            if upper:
                x = uppercase(x)
            content += "\n"+marker+x
        return content

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
        if len(ctx.message.mentions) > 0:
            player2 = await self.getPlayer(ctx.message.mentions[0].id, ctx, someone_else=True)
        else:
            player2 = await self.getPlayer(" ".join(ctx.message.content.split(" ")[1:]), ctx, someone_else=True)
        if player2 == None:
            return
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
        if len(ctx.message.content.split(" ")) < 3:
            return await self.bot.send_message(ctx.message.channel, "Equip what?")
        if ctx.message.content.split(" ")[1] == "weapon":
            success = player.changeEquip(ctx.message.content[14:])
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
        await self.removeItem(player.inv, inv[selection1])
        player.save()

    @commands.command(pass_context=True)
    async def goto(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        new_location = None
        for n in self.locations:
            if self.locations[n]["name"].lower() == ctx.message.content[6:].lower():
                new_location = n
        if new_location == None:
            return await self.bot.send_message(ctx.message.channel, "That location doesn't exist on your map.")
        k = player.location
        if k == n:
            return await self.bot.send_message(ctx.message.channel, "You're already there.")
        self.locations[k]["players"].remove(ctx.message.author.id)
        self.locations[n]["players"].append(ctx.message.author.id)
        player.location = self.locations[n]["id"]
        await self.bot.send_message(ctx.message.channel, "You arrived at {} in one piece.".format(self.locations[n]["name"]))
        player.save()

    @commands.command(pass_context=True)
    async def people(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        embed = discord.Embed(title="People currently in {}".format(self.locations[player.location]["name"]), description=await self.listPlayers(ctx, self.locations[player.location]), color=0xff1e69)
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True)
    async def talk(self, ctx):
        player1 = await self.getPlayer(ctx.message.author.id, ctx)
        location = self.locations[player1.location]
        options = [p for p in location["players"] if not self.getPlayerSync(p) == None and self.getPlayerSync(p).name.lower() == ctx.message.content[6:].lower()]
        if len(options) == 0:
            return await self.bot.send_message(ctx.message.channel, "That person isn't present.")
        if len(options) > 1:
            return await self.bot.send_message(ctx.message.channel, "There is more than one person with that name.")
            #names = map((lambda o: if hasattr(self.getPlayerSync(o), identifier): self.getPlayerSync(o).name+", "+self.getPlayerSync(o).identifier else: self.getPlayerSync(o).name), options)
            embed = discord.Embed(title="People with the name {}:".format(ctx.message.content[6:]), description=self.listArr(names, numbered=True))
            choice = await self.promptUser(ctx.message.author, ctx.message.channel, embed=embed)
            if not choice.isdigit():
                return await self.bot.send_message(ctx.message.channel, "Invalid selection.")
            if choice > options.length:
                return await self.bot.send_message(ctx.message.channel, "Invalid selection.")
            player2 = await self.getPlayer(options[int(choice) - 1], ctx, someone_else=True)
        else:
            player2 = await self.getPlayer(options[0], ctx, someone_else=True)
        conversation = Conversation(self, ctx.message.channel, player1, player2)
        result = await conversation.start()
        player1 = result[0]
        player2 = result[1]
        player1.save()
        player2.save()

    @commands.command(pass_context=True)
    async def map(self, ctx):
        player = await self.getPlayer(ctx.message.author.id, ctx)
        embed = discord.Embed(title="Locations", description=self.listLocations(), color=0xff1e69)
        await self.bot.send_message(ctx.message.channel, embed=embed)

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
        player.update()
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

def read_folder(path, filetype="json"):
    d = {}
    for root, directories, filenames in os.walk("data/crpg/{}".format(path)):
        for filename in filenames: 
            if filetype == "json":
                d[filename[:-5]] = fileIO(os.path.join(root,filename), "load")
            elif filetype == "obj":
                d[filename[:-4]] = loadPickle(os.path.join(root,filename))
    return d     

def setup(bot):
    global items
    items = read_folder("items")
    n = ChillRPG(bot)
    bot.add_cog(n)