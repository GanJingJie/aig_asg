import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

## declare global variable
choice = 0
level = 0

class Archer_HalJordan(Character):

    def __init__(self, world, image, projectile_image, base, position):

        Character.__init__(self, world, "archer", image)

        self.projectile_image = projectile_image

        self.base = base
        self.position = position
        self.move_target = GameEntity(world, "archer_move_target", None)
        self.target = None

        self.maxSpeed = 50
        self.min_target_distance = 100
        self.projectile_range = 100
        self.projectile_speed = 100

        seeking_state = ArcherStateSeeking_HalJordan(self)
        attacking_state = ArcherStateAttacking_HalJordan(self)
        ko_state = ArcherStateKO_HalJordan(self)
        fleeing_state = ArcherStateFleeing_HalJordan(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(ko_state)
        self.brain.add_state(fleeing_state)

        self.brain.set_state("seeking")

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
         
        Character.process(self, time_passed)

        ## levelling up in order
        global choice
        global level

        level_up_stats = ["ranged damage", "ranged cooldown"]
        if self.can_level_up():
            if choice == 2:
                choice = 0
            self.level_up(level_up_stats[choice])
            choice += 1
            level += 1

        if self.brain.active_state.name == "fleeing":
            if self.current_hp < self.max_hp:
                self.heal()

class ArcherStateSeeking_HalJordan(State):

    def __init__(self, archer):

        State.__init__(self, "seeking")
        self.archer = archer
        global level

        if level >= 4:
            self.archer.path_graph = self.archer.world.paths[3]
        else:
            self.archer.path_graph = self.archer.world.paths[0]


    def do_actions(self):

        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed


    def check_conditions(self):

        # check if opponent is in range
        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            opponent_distance = (self.archer.position - nearest_opponent.position).length()
            if opponent_distance <= self.archer.min_target_distance:
                    self.archer.target = nearest_opponent
                    return "attacking"
        
        if (self.archer.position - self.archer.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.archer.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
            
        return None

    def entry_actions(self):

        nearest_node = self.archer.path_graph.get_nearest_node(self.archer.position)

        self.path = pathFindAStar(self.archer.path_graph, \
                                  nearest_node, \
                                  self.archer.path_graph.nodes[self.archer.base.target_node_index])

        
        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.archer.move_target.position = self.path[0].fromNode.position

        else:
            self.archer.move_target.position = self.archer.path_graph.nodes[self.archer.base.target_node_index].position


class ArcherStateAttacking_HalJordan(State):

    def __init__(self, archer):

        State.__init__(self, "attacking")
        self.archer = archer

    def do_actions(self):

        archer = self.archer.position
        archerSpeed = self.archer.target.position - self.archer.position
        nearestEntity = self.archer.world.get_nearest_opponent(self.archer)

        #calculate the other point of line
        

        opponent_distance = (archer - self.archer.target.position).length()
        

        # opponent within range
        if opponent_distance <= self.archer.min_target_distance:
            self.archer.velocity = Vector2(0,0)
            #if intersect(archer,):
                #detect if movement is required
            if self.archer.current_ranged_cooldown <= 0:
                self.archer.ranged_attack(self.archer.target.position)

        else:
            self.archer.velocity = self.archer.target.position - self.archer.position
            if self.archer.velocity.length() > 0:
                self.archer.velocity.normalize_ip()
                self.archer.velocity *= self.archer.maxSpeed


    def check_conditions(self):
        opponent_distance = (self.archer.position - self.archer.target.position).length()

        if opponent_distance <= (self.archer.min_target_distance / 3) or self.archer.current_hp < self.archer.max_hp * 0.5:
            return "fleeing"

        # target is gone
        if self.archer.world.get(self.archer.target.id) is None or self.archer.target.ko:
            self.archer.target = None
            return "seeking"
        
        return None

    def entry_actions(self):

        return None



class ArcherStateKO_HalJordan(State):

    def __init__(self, archer):

        State.__init__(self, "ko")
        self.archer = archer

    def do_actions(self):

        return None


    def check_conditions(self):

        # respawned
        if self.archer.current_respawn_time <= 0:
            self.archer.current_respawn_time = self.archer.respawn_time
            self.archer.ko = False
            if level >= 4:
                self.archer.path_graph = self.archer.world.paths[3]
            else:
                self.archer.path_graph = self.archer.world.paths[0]
            return "seeking"
            
        return None

    def entry_actions(self):

        self.archer.current_hp = self.archer.max_hp
        self.archer.position = Vector2(self.archer.base.spawn_position)
        self.archer.velocity = Vector2(0, 0)
        self.archer.target = None

        return None

class ArcherStateFleeing_HalJordan(State):

    def __init__(self,archer):

        State.__init__(self, "fleeing")
        self.archer = archer

    def do_actions(self):

        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed
        

    def check_conditions(self):
        
        # target safe
         if self.archer.world.get(self.archer.target.id) is None or self.archer.target.ko:
            self.archer.target = None
            return "attacking"

    def entry_actions(self):
        
        flee_direction = (self.archer.position - self.archer.target.position).normalize()
        flee_distance = -1000
        self.archer.move_target.position = self.archer.position - flee_direction * flee_distance

# Checking if vectors intersect
def ccw(A,B,C):
    
    return (C.y-A.y) * (B.x-A.x) > (B.y-A.y) * (C.x-A.x)

def intersect(A,B,C,D):

    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)
