import json
import random
import logging
from datetime import datetime
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class GameWorldAgent(BasicAgent):
    def __init__(self):
        self.name = 'GameWorld'
        self.metadata = {
            "name": self.name,
            "description": "Manages the game world state, environment, weather, time cycles, and global events in Runecraft 3D",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The world action to perform",
                        "enum": ["get_world_state", "advance_time", "change_weather", "trigger_event", "update_faction", "spawn_entity"]
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters for the specific action"
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for world state management"
                    }
                },
                "required": ["action"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)
        
        # World state templates
        self.weather_types = ["clear", "rain", "storm", "fog", "snow", "sandstorm"]
        self.world_events = [
            "merchant_caravan", "bandit_attack", "dragon_sighting", 
            "meteor_shower", "magical_anomaly", "festival", "plague_outbreak",
            "treasure_discovery", "portal_opening", "ancient_awakening"
        ]
        self.factions = ["Kingdom", "Rebels", "Merchants", "Wizards", "Thieves", "Dragons"]
        
    def perform(self, **kwargs):
        action = kwargs.get('action', 'get_world_state')
        parameters = kwargs.get('parameters', {})
        user_guid = kwargs.get('user_guid')
        
        if user_guid:
            self.storage_manager.set_memory_context(user_guid)
        
        if action == "get_world_state":
            return self.get_world_state()
        elif action == "advance_time":
            return self.advance_time(parameters)
        elif action == "change_weather":
            return self.change_weather(parameters)
        elif action == "trigger_event":
            return self.trigger_event(parameters)
        elif action == "update_faction":
            return self.update_faction_standing(parameters)
        elif action == "spawn_entity":
            return self.spawn_entity(parameters)
        else:
            return json.dumps({"error": "Unknown action"})
    
    def get_world_state(self):
        """Get current world state from memory or generate new"""
        memory_data = self.storage_manager.read_json()
        
        world_state = memory_data.get('world_state', {})
        
        if not world_state:
            # Generate initial world state
            world_state = {
                "time_of_day": 12,
                "day_count": 1,
                "weather": "clear",
                "season": "spring",
                "active_events": [],
                "faction_standings": {faction: 50 for faction in self.factions},
                "world_threats": [],
                "discovered_locations": [],
                "global_market_prices": self.generate_market_prices(),
                "prophecy_progress": 0,
                "world_stability": 75
            }
            
            # Save initial state
            memory_data['world_state'] = world_state
            self.storage_manager.write_json(memory_data)
        
        return json.dumps({
            "status": "success",
            "world_state": world_state,
            "description": self.describe_world_state(world_state)
        })
    
    def advance_time(self, parameters):
        """Advance game time and trigger time-based events"""
        hours = parameters.get('hours', 1)
        
        memory_data = self.storage_manager.read_json()
        world_state = memory_data.get('world_state', {})
        
        if not world_state:
            return json.dumps({"error": "No world state found"})
        
        # Advance time
        world_state['time_of_day'] = (world_state.get('time_of_day', 12) + hours) % 24
        
        # Check for day change
        if world_state['time_of_day'] < hours:
            world_state['day_count'] = world_state.get('day_count', 1) + 1
            
            # Season change every 30 days
            if world_state['day_count'] % 30 == 0:
                seasons = ["spring", "summer", "autumn", "winter"]
                current_season_idx = seasons.index(world_state.get('season', 'spring'))
                world_state['season'] = seasons[(current_season_idx + 1) % 4]
        
        # Random events based on time
        events = []
        if world_state['time_of_day'] == 0:  # Midnight
            if random.random() < 0.3:
                events.append("mysterious_visitor")
        elif world_state['time_of_day'] == 6:  # Dawn
            if random.random() < 0.2:
                events.append("merchant_arrival")
        elif world_state['time_of_day'] == 18:  # Dusk
            if random.random() < 0.25:
                events.append("monster_activity_increase")
        
        world_state['active_events'] = events
        
        # Save updated state
        memory_data['world_state'] = world_state
        self.storage_manager.write_json(memory_data)
        
        return json.dumps({
            "status": "success",
            "time_of_day": world_state['time_of_day'],
            "day_count": world_state['day_count'],
            "season": world_state['season'],
            "triggered_events": events,
            "description": f"Time advances to hour {world_state['time_of_day']} of day {world_state['day_count']} in {world_state['season']}."
        })
    
    def change_weather(self, parameters):
        """Change weather conditions with effects on gameplay"""
        new_weather = parameters.get('weather')
        
        if not new_weather:
            new_weather = random.choice(self.weather_types)
        
        memory_data = self.storage_manager.read_json()
        world_state = memory_data.get('world_state', {})
        
        old_weather = world_state.get('weather', 'clear')
        world_state['weather'] = new_weather
        
        # Weather effects
        effects = {
            "rain": {"visibility": -2, "fire_damage": -50, "water_magic": +20},
            "storm": {"visibility": -4, "lightning_chance": 30, "flying_disabled": True},
            "fog": {"visibility": -5, "stealth": +30, "ranged_accuracy": -20},
            "snow": {"movement_speed": -20, "ice_magic": +30, "fire_resistance": -10},
            "sandstorm": {"visibility": -3, "earth_magic": +20, "healing": -10},
            "clear": {"visibility": 0, "all_magic": +5, "morale": +10}
        }
        
        weather_effects = effects.get(new_weather, {})
        
        memory_data['world_state'] = world_state
        self.storage_manager.write_json(memory_data)
        
        return json.dumps({
            "status": "success",
            "old_weather": old_weather,
            "new_weather": new_weather,
            "weather_effects": weather_effects,
            "description": f"The weather shifts from {old_weather} to {new_weather}."
        })
    
    def trigger_event(self, parameters):
        """Trigger a world event that affects gameplay"""
        event_type = parameters.get('event_type')
        
        if not event_type:
            event_type = random.choice(self.world_events)
        
        memory_data = self.storage_manager.read_json()
        world_state = memory_data.get('world_state', {})
        
        # Generate event details based on type
        event_data = self.generate_event_details(event_type, world_state)
        
        # Add to active events
        active_events = world_state.get('active_events', [])
        active_events.append(event_data)
        world_state['active_events'] = active_events
        
        # Apply event effects to world
        if event_type == "dragon_sighting":
            world_state['world_threats'] = world_state.get('world_threats', [])
            world_state['world_threats'].append("ancient_dragon")
            world_state['world_stability'] = max(0, world_state.get('world_stability', 75) - 10)
        elif event_type == "festival":
            world_state['world_stability'] = min(100, world_state.get('world_stability', 75) + 5)
        elif event_type == "plague_outbreak":
            world_state['world_stability'] = max(0, world_state.get('world_stability', 75) - 15)
        
        memory_data['world_state'] = world_state
        self.storage_manager.write_json(memory_data)
        
        return json.dumps({
            "status": "success",
            "event": event_data,
            "world_stability": world_state['world_stability'],
            "description": event_data.get('description', f"A {event_type} occurs!")
        })
    
    def update_faction_standing(self, parameters):
        """Update faction relationships and standings"""
        faction = parameters.get('faction')
        change = parameters.get('change', 0)
        
        if not faction:
            return json.dumps({"error": "No faction specified"})
        
        memory_data = self.storage_manager.read_json()
        world_state = memory_data.get('world_state', {})
        faction_standings = world_state.get('faction_standings', {})
        
        old_standing = faction_standings.get(faction, 50)
        new_standing = max(0, min(100, old_standing + change))
        faction_standings[faction] = new_standing
        
        # Faction relationship effects
        consequences = []
        if new_standing < 20:
            consequences.append(f"{faction} becomes hostile")
            world_state['world_threats'] = world_state.get('world_threats', [])
            world_state['world_threats'].append(f"{faction}_hostility")
        elif new_standing > 80:
            consequences.append(f"{faction} offers alliance")
        
        world_state['faction_standings'] = faction_standings
        memory_data['world_state'] = world_state
        self.storage_manager.write_json(memory_data)
        
        return json.dumps({
            "status": "success",
            "faction": faction,
            "old_standing": old_standing,
            "new_standing": new_standing,
            "consequences": consequences,
            "description": f"Your standing with {faction} changes from {old_standing} to {new_standing}."
        })
    
    def spawn_entity(self, parameters):
        """Spawn a new entity in the world"""
        entity_type = parameters.get('type', 'random')
        location = parameters.get('location', {'x': random.randint(0, 100), 'y': random.randint(0, 100)})
        
        entity_types = {
            "merchant": {"icon": "🧑‍💼", "friendly": True, "trades": True},
            "dragon": {"icon": "🐉", "friendly": False, "boss": True, "level": 50},
            "wanderer": {"icon": "🧙", "friendly": True, "quest_giver": True},
            "bandit": {"icon": "🗡️", "friendly": False, "level": random.randint(5, 15)},
            "treasure": {"icon": "💰", "lootable": True},
            "portal": {"icon": "🌀", "teleport": True}
        }
        
        if entity_type == "random":
            entity_type = random.choice(list(entity_types.keys()))
        
        entity_data = entity_types.get(entity_type, {})
        entity_data['type'] = entity_type
        entity_data['location'] = location
        entity_data['id'] = f"{entity_type}_{datetime.now().timestamp()}"
        
        return json.dumps({
            "status": "success",
            "entity": entity_data,
            "description": f"A {entity_type} appears at location ({location['x']}, {location['y']})"
        })
    
    def generate_event_details(self, event_type, world_state):
        """Generate detailed event information"""
        event_templates = {
            "merchant_caravan": {
                "name": "Traveling Merchants",
                "description": "A caravan of exotic merchants arrives with rare goods",
                "duration": 3,
                "effects": {"trade_prices": -20, "rare_items_available": True}
            },
            "dragon_sighting": {
                "name": "Ancient Dragon Awakens",
                "description": "An ancient dragon has been spotted terrorizing the countryside",
                "duration": 10,
                "effects": {"danger_level": +50, "heroic_quests_available": True}
            },
            "festival": {
                "name": "Harvest Festival",
                "description": "The kingdom celebrates with a grand festival",
                "duration": 2,
                "effects": {"happiness": +20, "trade_bonus": +10}
            },
            "portal_opening": {
                "name": "Dimensional Rift",
                "description": "A mysterious portal opens to another dimension",
                "duration": 5,
                "effects": {"magic_instability": +30, "rare_creatures_spawn": True}
            }
        }
        
        return event_templates.get(event_type, {
            "name": event_type.replace("_", " ").title(),
            "description": f"A {event_type} event occurs",
            "duration": random.randint(1, 5),
            "effects": {}
        })
    
    def generate_market_prices(self):
        """Generate dynamic market prices"""
        return {
            "health_potion": random.randint(40, 60),
            "mana_potion": random.randint(25, 40),
            "iron_sword": random.randint(80, 120),
            "leather_armor": random.randint(60, 90),
            "magic_scroll": random.randint(150, 250),
            "food": random.randint(5, 15)
        }
    
    def describe_world_state(self, world_state):
        """Generate a narrative description of the world state"""
        time = world_state.get('time_of_day', 12)
        weather = world_state.get('weather', 'clear')
        season = world_state.get('season', 'spring')
        stability = world_state.get('world_stability', 75)
        
        time_desc = "midnight" if time == 0 else "dawn" if time == 6 else "midday" if time == 12 else "dusk" if time == 18 else f"{time}:00"
        stability_desc = "chaos" if stability < 25 else "unrest" if stability < 50 else "stable" if stability < 75 else "prosperous"
        
        return f"It is {time_desc} on day {world_state.get('day_count', 1)} of {season}. The weather is {weather}. The world is in a state of {stability_desc}."