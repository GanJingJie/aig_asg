import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

choice = 0
level = 0

class Wizard_TeamA(Character):

    def __init__(self, world, image, projectile_image, base, position, explosion_image = None):

        Character.__init__(self, world, "wizard", image)

        self.projectile_image = projectile_image
        self.explosion_image = explosion_image

        self.base = base
        self.position = position
        self.move_target = GameEntity(world, "wizard_move_target", None)
        self.target = None

        self.maxSpeed = 50
        self.min_target_distance = 100
        self.projectile_range = 100
        self.projectile_speed = 100

        seeking_state = WizardStateSeeking_TeamA(self)
        attacking_state = WizardStateAttacking_TeamA(self)
        fleeing_state = WizardStateFleeing_TeamA(self)
        ko_state = WizardStateKO_TeamA(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(fleeing_state)
        self.brain.add_state(ko_state)

        self.brain.set_state("seeking")

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
        
        Character.process(self, time_passed)

        global level
        global choice

        if self.current_hp < 100:
            self.heal()

        level_up_stats = ["ranged cooldown", "ranged damage", "ranged cooldown"]
        if self.can_level_up():
            self.level_up(level_up_stats[choice])
            level += 1
            choice += 1
            
            if choice == 2:
                choice = 0


class WizardStateSeeking_TeamA(State):

    def __init__(self, wizard):

        State.__init__(self, "seeking")
        self.wizard = wizard

        if level >= 4:
            self.wizard.path_graph = self.wizard.world.paths[2]
        else:
            self.wizard.path_graph = self.wizard.world.paths[1]

    def do_actions(self):

        self.wizard.velocity = self.wizard.move_target.position - self.wizard.position
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip();
            self.wizard.velocity *= self.wizard.maxSpeed

    def check_conditions(self):

        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)

        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position - nearest_opponent.position).length()
            if opponent_distance <= 60:
                if nearest_opponent.name == "orc" or (nearest_opponent.name == "knight" and nearest_opponent.target == self.wizard):
                    self.wizard.target = nearest_opponent
                    return "fleeing"
                
        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position - nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                    self.wizard.target = nearest_opponent
                    return "attacking"
        
        if (self.wizard.position - self.wizard.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.wizard.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
                   
        return None

    def entry_actions(self):

        nearest_node = self.wizard.path_graph.get_nearest_node(self.wizard.position)

        self.path = pathFindAStar(self.wizard.path_graph, \
                                  nearest_node, \
                                  self.wizard.path_graph.nodes[self.wizard.base.target_node_index])

        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.wizard.move_target.position = self.path[0].fromNode.position

        else:
            self.wizard.move_target.position = self.wizard.path_graph.nodes[self.wizard.base.target_node_index].position

class WizardStateAttacking_TeamA(State):

    def __init__(self, wizard):

        State.__init__(self, "attacking")
        self.wizard = wizard

    def do_actions(self):

        opponent_distance = (self.wizard.position - self.wizard.target.position).length()

        # opponent within range
        if opponent_distance <= self.wizard.min_target_distance:
            self.wizard.velocity = Vector2(0, 0)
            if self.wizard.current_ranged_cooldown <= 0:
                self.wizard.ranged_attack(self.wizard.target.position, self.wizard.explosion_image)

        else:
            self.wizard.velocity = self.wizard.target.position - self.wizard.position
            if self.wizard.velocity.length() > 0:
                self.wizard.velocity.normalize_ip();
                self.wizard.velocity *= self.wizard.maxSpeed


    def check_conditions(self):

        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position - nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                if opponent_distance <= 60:
                    if nearest_opponent.name == "orc" or nearest_opponent.name == "knight":
                        self.wizard.target = nearest_opponent
                        return "fleeing"
                    elif (nearest_opponent.name == "archer" or nearest_opponent.name == "wizard") and nearest_opponent.target == self.wizard:
                         self.wizard.target = nearest_opponent
                         return "fleeing"                       
    
        if self.wizard.current_hp < 80:
            return "fleeing"

        # target is gone
        if self.wizard.world.get(self.wizard.target.id) is None or self.wizard.target.ko:
            self.wizard.target = None
            return "seeking"
        
            
        return None

    def entry_actions(self):

        return None

class WizardStateFleeing_TeamA(State):

    def __init__(self, wizard):

        State.__init__(self, "fleeing")
        self.wizard = wizard

    def do_actions(self):

        self.wizard.velocity = self.wizard.move_target.position - self.wizard.position
        
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip();
            self.wizard.velocity *= self.wizard.maxSpeed

        if self.wizard.current_ranged_cooldown <= 0:
            self.wizard.ranged_attack(self.wizard.target.position, self.wizard.explosion_image)

    def check_conditions(self):

        # target is gone
        if self.wizard.world.get(self.wizard.target.id) is None or self.wizard.target.ko:
            self.wizard.target = None
            return "seeking"

        # if healed up
        if self.wizard.current_hp > 100:
            return "seeking"
        
        if (self.wizard.position - self.wizard.move_target.position).length() < 8:
 
            # continue on path
            if self.current_connection < self.path_length:
                try:
                    self.wizard.move_target.position = self.path[self.current_connection].fromNode.position
                    self.current_connection -= 1
                    
                except:
                         
                    self.wizard.move_target.position = self.wizard.base.position     
                
        return None

    def entry_actions(self):

        #flee_direction = (self.wizard.position - self.wizard.target.position).normalize()
        #flee_distance = -1000
        #self.wizard.move_target.position = self.wizard.position - flee_direction * flee_distance
        #self.wizard.move_target.position = self.wizard.base.spawn_position

        nearest_node = self.wizard.path_graph.get_nearest_node(self.wizard.position)

        self.path = pathFindAStar(self.wizard.path_graph, \
                                  nearest_node, \
                                  self.wizard.world.graph.get_nearest_node(self.wizard.base.position))
        
        self.path_length = len(self.path)

        if (self.path_length > 1):
            self.current_connection = 0
            self.wizard.move_target.position = self.path[1].fromNode.position
        if (self.path_length > 0):
            self.current_connection = 0
            self.wizard.move_target.position = self.path[0].fromNode.position
        else:
            self.wizard.move_target.position = self.wizard.path_graph.nodes[self.wizard.base.spawn_node_index].position
            
        
class WizardStateKO_TeamA(State):

    def __init__(self, wizard):

        State.__init__(self, "ko")
        self.wizard = wizard

    def do_actions(self):

        return None


    def check_conditions(self):

        # respawned
        if self.wizard.current_respawn_time <= 0:
            self.wizard.current_respawn_time = self.wizard.respawn_time
            self.wizard.ko = False
            if level >= 4:
                self.wizard.path_graph = self.wizard.world.paths[2]
                
            else:
                self.wizard.path_graph = self.wizard.world.paths[1]
                
            return "seeking"
            
        return None

    def entry_actions(self):

        self.wizard.current_hp = self.wizard.max_hp
        self.wizard.position = Vector2(self.wizard.base.spawn_position)
        self.wizard.velocity = Vector2(0, 0)
        self.wizard.target = None

        return None
