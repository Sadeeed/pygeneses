import os
import shutil
import pygame

from player_class import Player
from particle_class import Particle
from helpers import *
from global_constants import *
from reinforce import ReinforceModel

model_to_class = {'reinforce': 'ReinforceModel'}

class PrimaVita:

    def __init__(self, initial_population=10, state_size=20, action_size=13, max_regenerations=0, model_updates=10):
        self.log_dir = 'Players_Data'
        self.initial_population = initial_population
        self.state_size = state_size
        self.action_size = action_size
        self.time = -1
        self.regenerate_times = 0
        self.max_regenerations = max_regenerations
        self.allow_regenerate = True if max_regenerations > 0 else False
        self.food_regen_condition_is_met = False
        self.players = []
        self.killed = []
        self.my_particles = []
        self.model = 0
        self.model_updates = model_updates

        self.reset_logs()

    def init(self, model_name='reinforce'):
        # Initialise pygame
        pygame.init()

        # Title
        pygame.display.set_caption("Prima Vita")

        # Generate initial population
        self.players = regenerate_species(TIME)

        for j in range(NUMBER_OF_PARTICLES):
            self.my_particles.append(Particle())

        self.my_particles = check_particles(self.my_particles)

        self.model = eval(model_to_class[model_name])(self.initial_population, self.state_size, self.action_size)

        screen.fill((0, 178, 0))

        for event in pygame.event.get():
            pass

        pygame.display.update()

        eval(model_to_class[model_name])(self.initial_population, self.state_size, self.action_size)

    def reset_logs(self):
        if os.path.exists(self.log_dir):
            shutil.rmtree(self.log_dir)

        os.mkdir(self.log_dir)

    def pad_state(self, state, maxlen):
        if len(state) > maxlen:
            return state[:maxlen]
        elif len(state) < maxlen:
            new_state = np.zeros((maxlen,))
            new_state[:len(state)] = state
            return new_state
        elif len(state) == maxlen:
            return state

    def get_current_state(self):
        if(len(self.killed) == len(self.players)):
            return -1

        initial_state = []
        for i in range(len(self.players)):
            if type(self.players[i]) != int:
                env_particles,env_particle_distance = food_in_env(self.players[i], self.my_particles)
                env_food_vector = getFoodVector(self.players[i], env_particles, self.my_particles)
                env_food_vector = sum(env_food_vector, [])

                env_players, env_player_distance = players_in_env(self.players[i], self.players)
                env_player_vector = getPlayerVector(self.players[i], env_players, self.players)
                env_player_vector = sum(env_player_vector, [])

                temp_state = [env_food_vector, env_player_vector]
                temp_state = sum(temp_state, [])
                initial_state.append(np.array(temp_state))
            else:
                initial_state.append(np.array([0]))

        initial_state = [self.pad_state(state, self.state_size-1) for state in initial_state]
        initial_state = [np.append(initial_state[i], self.players[i].energy) if type(self.players[i]) != int else np.append(initial_state[i], -100) for i in range(len(self.players))]

        return np.array(initial_state)

    def take_action(self, idx, state):
        action = self.model.predict_action(idx, state)

        reward = 0
        mate_idx = -1

        screen.fill((0, 178, 0))

        for event in pygame.event.get():
            pass

        if action == 0: # Left
            self.players[idx].change_player_xposition(-SPEED)
            reward = -2
        elif action == 1: # Right
            self.players[idx].change_player_xposition(SPEED)
            reward = -2
        elif action == 2: # Up
            self.players[idx].change_player_yposition(-SPEED)
            reward = -2
        elif action == 3: # Down
            self.players[idx].change_player_yposition(SPEED)
            reward = -2
        elif action == 4: # Up Left
            self.players[idx].change_player_yposition(-SPEED)
            self.players[idx].change_player_xposition(-SPEED)
            reward = -2
        elif action == 5: # Up Right
            self.players[idx].change_player_yposition(-SPEED)
            self.players[idx].change_player_xposition(SPEED)
            reward = -2
        elif action == 6: # Down Left
            self.players[idx].change_player_yposition(SPEED)
            self.players[idx].change_player_xposition(-SPEED)
            reward = -2
        elif action == 7: # Down Right
            self.players[idx].change_player_yposition(SPEED)
            self.players[idx].change_player_xposition(SPEED)
            reward = -2
        elif action == 8: # Stay
            self.players[idx].energy -= 2
            reward = -50
            self.players[idx].update_history(action, self.time, reward)
        elif action == 9: #Ingestion
            food_particle = food_nearby(self.players[idx], self.my_particles)
            if(food_particle != -1):
                self.players[idx].ingesting_food(food_particle, self.time)
                self.my_particles[food_particle] = 0
                reward = 5
                self.players[idx].update_history(action, self.time, reward)
            else:
                reward = -10
                self.players[idx].update_history(action, self.time, reward, failed=True)
        elif action == 10:  # Asexual_reproduction
            if(type(self.players[idx]) != int and not self.players[idx].is_impotent and
                type(self.players[idx]) != int and (self.time - self.players[idx].born_at) in range(10, 61)):
                reward = 0
                offspring_players, offspring_ids = self.players[idx].asexual_reproduction(len(self.players), self.time)
                for offspring_player in offspring_players:
                    self.players.append(offspring_player)
                self.initial_population += len(offspring_players)
                self.players[idx].update_history(action, self.time, reward, num_offspring = len(offspring_ids), offspring_ids = offspring_ids)
                self.players[idx].write_data()   #Writes data to file
                self.players[idx] = 0
                self.killed.append(idx)

                self.model.add_agents(idx, len(offspring_players))
                self.model.kill_agent(idx)
            else:
                reward = -10
                self.players[idx].update_history(action, self.time, reward, failed=True)
        elif action == 11:  # Sexual_reproduction
            if(self.players[idx].mating_begin_time == 0):
                mate_idx = search_mate(self.players[idx], self.players, self.time)
                if(mate_idx != -1):
                    mating_begin_time = self.time
                    reward = 4
                    offspring_players, offspring_ids = self.players[idx].sexual_reproduction(mating_begin_time, len(self.players), True)
                    self.players[mate_idx].sexual_reproduction(mating_begin_time, len(self.players))
                    for offspring_player in offspring_players:
                        self.players.append(offspring_player)
                    self.initial_population += len(offspring_players)
                    self.players[idx].update_history(action, mating_begin_time, reward, num_offspring = len(offspring_ids), offspring_ids = offspring_ids, mate_id = mate_idx)
                    self.players[mate_idx].update_history(action, mating_begin_time, reward, num_offspring = len(offspring_ids), offspring_ids = offspring_ids, mate_id = idx)

                    dominant_percent = random.randint(0, 10) * 10
                    recessive_percent = 100 - dominant_percent
                    offsprings = len(players) - len(agents)
                    num_dominant = round(offsprings * (dominant_percent / 100))
                    num_recessive = offsprings - num_dominant

                    dominant_idx = idx if self.players[idx].energy > self.players[mate_idx].energy else mate_idx
                    recessive_idx = idx if dominant_idx == mate_idx else mate_idx

                    self.model.add_agents(dominant_idx, num_dominant)
                    self.model.add_agets(recessive_idx, num_recessive)
                else:
                    reward = -10
                    self.players[idx].update_history(action, TIME, reward, failed=True)

            else:
                reward = -10
                self.players[idx].update_history(action, TIME, reward, failed=True)
        elif action == 12:      #Fight
            if(self.players[idx].fighting_with == -1):
                enemy = search_enemy(self.players[idx], self.players)
                if(enemy != -1):
                    reward = -1
                    self.players[idx].fighting_with = enemy
                    self.players[enemy].fighting_with = idx
                    self.players[idx].energy -= 10
                    self.players[enemy].energy -= 10
                    self.players[idx].fighting_with = -1
                    self.players[enemy].fighting_with = -1
                    self.players[idx].update_history(action, self.time, reward, fight_with = enemy )
                    self.players[enemy].update_history(action, self.time, reward, fight_with = idx)
                else:
                    reward = -10
                    self.players[idx].update_history(action, self.time, reward, failed=True)
            else:
                reward = -10
                self.players[idx].update_history(action, self.time, reward, failed=True)

        if action <=7 :
            if self.players[idx].cannot_move == False:
                self.players[idx].update_history(action, self.time, reward)
            else:
                self.players[idx].update_history(action, self.time, reward, failed=True)

        if (FOOD_REGEN_CONDITION_IS_MET):                                       #FOOD REGEN PART always false for now
            print("Food regenerated!")
            self.my_particles, _ = refreshParticles(self.my_particles, len(self.my_particles))
            self.food_regen_condition_is_met = False

        # Show particles
        for j in range(len(self.my_particles)):
            if(type(self.my_particles[j]) != int):
                self.my_particles[j].show_particle()

        now_time = self.time

        for i in range(len(self.players)):
            if(i not in self.killed):
                if(i == idx):
                    self.model.rewards[idx].append(reward)
                    self.model.scores[idx] += reward

                env_particles, env_particle_distance = food_in_env(self.players[i], self.my_particles)
                self.players[i].food_near = env_particle_distance
                env_food_vector = getFoodVector(self.players[i], env_particles, self.my_particles)   #VECTOR FOOD

                env_players, env_player_distance = players_in_env(self.players[i], self.players)
                self.players[i].players_near = env_player_distance
                env_player_vector = getPlayerVector(self.players[i], env_players, self.players)                    #VECTOR player

                for index in range(0, len(env_particles)):                #change color of food in env_particles
                    local = env_particles[index]
                    if type(self.my_particles[local]) != int:
                        self.my_particles[local].show_close()

                if not env_players:
                    self.players[i].show_player()
                else:
                    self.players[i].show_close()

                if(type(self.players[i]) != int and self.players[i].ingesting_begin_time != 0 and
                    self.time - self.players[i].ingesting_begin_time >= 1):
                    self.players[i].food_ate += 1
                    self.players[i].ingesting_begin_time = 0
                    self.players[i].cannot_move = False

                if(type(self.players[i]) != int and self.players[i].mating_begin_time != 0 and
                    self.time - self.players[i].mating_begin_time >= 2):
                    self.players[i].mating_begin_time = 0
                    self.players[i].cannot_move = False

                if(type(self.players[i]) != int and self.players[i].energy <= 0):
                    self.players[i].write_data()
                    self.players[i] = 0
                    self.killed.append(i)
                    self.model.kill_agent(i)

                if(type(self.players[i]) != int and now_time - self.players[i].born_at >= MAX_AGE):
                    self.players[i].write_data()
                    self.players[i] = 0
                    self.killed.append(i)
                    self.model.kill_agent(i)

        if(now_time % self.model_updates == 0):
            self.model.update_all_agents()

        # Update the window
        pygame.display.update()

    def update_time(self):
        self.time += 1