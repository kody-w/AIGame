import json
import random
import logging
from datetime import datetime  # Added missing import
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class NPCDialogueAgent(BasicAgent):
    def __init__(self):
        self.name = 'NPCDialogue'
        self.metadata = {
            "name": self.name,
            "description": "Generates dynamic NPC dialogues, personalities, and interactions based on world state and player history",
            "parameters": {
                "type": "object",
                "properties": {
                    "npc_name": {
                        "type": "string",
                        "description": "Name of the NPC"
                    },
                    "npc_type": {
                        "type": "string",
                        "description": "Type of NPC (merchant, guard, questgiver, etc.)"
                    },
                    "player_action": {
                        "type": "string",
                        "description": "What the player said or did"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context like location, time, player reputation"
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for personalized NPC memories"
                    }
                },
                "required": ["npc_type"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)
        
        # NPC personality traits
        self.personality_traits = [
            "friendly", "suspicious", "greedy", "helpful", "mysterious",
            "nervous", "arrogant", "wise", "cunning", "jovial"
        ]
        
        # NPC archetypes with dialogue patterns
        self.npc_archetypes = {
            "merchant": {
                "greetings": ["Welcome, traveler!", "Looking to trade?", "Finest goods in the realm!"],
                "interests": ["trade", "profit", "goods", "customers"],
                "knowledge": ["prices", "trade_routes", "other_merchants", "rare_items"]
            },
            "guard": {
                "greetings": ["Halt! State your business.", "Move along, citizen.", "Keep the peace."],
                "interests": ["order", "law", "security", "threats"],
                "knowledge": ["crime", "wanted_criminals", "city_laws", "recent_incidents"]
            },
            "questgiver": {
                "greetings": ["Ah, a capable adventurer!", "Perhaps you can help...", "I have a task..."],
                "interests": ["quests", "problems", "rewards", "heroes"],
                "knowledge": ["local_problems", "ancient_lore", "dungeon_locations", "mysteries"]
            },
            "innkeeper": {
                "greetings": ["Welcome to my inn!", "Need a room?", "Ale and a bed, friend?"],
                "interests": ["gossip", "comfort", "travelers", "local_news"],
                "knowledge": ["rumors", "local_events", "traveler_stories", "town_history"]
            },
            "wizard": {
                "greetings": ["The arcane calls...", "Magic flows through all.", "Ah, I sense power in you."],
                "interests": ["magic", "knowledge", "artifacts", "prophecies"],
                "knowledge": ["spells", "enchantments", "magical_theory", "ancient_mysteries"]
            }
        }
    
    def perform(self, **kwargs):
        npc_name = kwargs.get('npc_name', self.generate_npc_name())
        npc_type = kwargs.get('npc_type', 'villager')
        player_action = kwargs.get('player_action', 'greet')
        context = kwargs.get('context', {})
        user_guid = kwargs.get('user_guid')
        
        if user_guid:
            self.storage_manager.set_memory_context(user_guid)
        
        # Get or create NPC memory
        npc_data = self.get_or_create_npc(npc_name, npc_type)
        
        # Generate dialogue based on context
        dialogue_response = self.generate_dialogue(npc_data, player_action, context)
        
        # Update NPC memory with this interaction
        self.update_npc_memory(npc_name, player_action, dialogue_response)
        
        return json.dumps({
            "status": "success",
            "npc": npc_data,
            "dialogue": dialogue_response['dialogue'],
            "emotion": dialogue_response['emotion'],
            "options": dialogue_response.get('options', []),
            "quest_offer": dialogue_response.get('quest_offer'),
            "trade_offer": dialogue_response.get('trade_offer')
        })
    
    def get_or_create_npc(self, npc_name, npc_type):
        """Get existing NPC data or create new NPC"""
        memory_data = self.storage_manager.read_json()
        npcs = memory_data.get('npcs', {})
        
        if npc_name not in npcs:
            # Create new NPC with personality and backstory
            npc_data = {
                "name": npc_name,
                "type": npc_type,
                "personality": random.choice(self.personality_traits),
                "disposition": 50,  # Neutral starting disposition
                "met_player": False,
                "interaction_count": 0,
                "memories": [],
                "backstory": self.generate_backstory(npc_type),
                "inventory": self.generate_npc_inventory(npc_type),
                "knowledge": self.npc_archetypes.get(npc_type, {}).get('knowledge', []),
                "current_mood": "neutral",
                "secrets": self.generate_secrets(npc_type) if random.random() < 0.3 else None
            }
            npcs[npc_name] = npc_data
            memory_data['npcs'] = npcs
            self.storage_manager.write_json(memory_data)
        else:
            npc_data = npcs[npc_name]
            npc_data['interaction_count'] += 1
        
        return npc_data
    
    def generate_dialogue(self, npc_data, player_action, context):
        """Generate contextual dialogue based on NPC personality and situation"""
        personality = npc_data['personality']
        disposition = npc_data['disposition']
        npc_type = npc_data['type']
        met_before = npc_data['met_player']
        
        # Get archetype dialogue patterns
        archetype = self.npc_archetypes.get(npc_type, {})
        
        # Determine emotion based on personality and disposition
        emotion = self.determine_emotion(personality, disposition, player_action)
        
        # Generate base dialogue
        if player_action == "greet":
            if not met_before:
                dialogue = self.generate_first_meeting(npc_data, archetype)
                npc_data['met_player'] = True
            else:
                dialogue = self.generate_greeting(npc_data, archetype, disposition)
        elif player_action == "threaten":
            dialogue = self.generate_threat_response(npc_data, disposition)
            emotion = "afraid" if disposition < 30 else "angry"
            npc_data['disposition'] = max(0, disposition - 10)
        elif player_action == "compliment":
            dialogue = self.generate_compliment_response(npc_data)
            emotion = "happy"
            npc_data['disposition'] = min(100, disposition + 5)
        elif player_action == "ask_quest":
            dialogue = self.generate_quest_dialogue(npc_data, context)
        elif player_action == "trade":
            dialogue = self.generate_trade_dialogue(npc_data)
        else:
            dialogue = self.generate_contextual_dialogue(npc_data, player_action, context)
        
        # Generate response options for player
        options = self.generate_response_options(npc_data, context)
        
        # Check for special offers
        response = {
            "dialogue": dialogue,
            "emotion": emotion,
            "options": options
        }
        
        # Add quest offer if appropriate
        if npc_type == "questgiver" and disposition > 40:
            response["quest_offer"] = self.generate_quest_offer(npc_data, context)
        
        # Add trade offer if merchant
        if npc_type == "merchant":
            response["trade_offer"] = True
        
        return response
    
    def generate_first_meeting(self, npc_data, archetype):
        """Generate dialogue for first meeting"""
        greetings = archetype.get('greetings', ["Hello there."])
        base_greeting = random.choice(greetings)
        
        personality_modifiers = {
            "friendly": " It's so nice to meet new people!",
            "suspicious": " You're not from around here, are you?",
            "mysterious": " Fate brings us together, it seems.",
            "nervous": " I-I don't usually talk to strangers...",
            "arrogant": " I suppose you've heard of me?",
            "wise": " I sense great potential in you, young one."
        }
        
        modifier = personality_modifiers.get(npc_data['personality'], "")
        
        # Fixed: Properly extract first sentence from backstory
        backstory_parts = npc_data['backstory'].split('.')
        if backstory_parts and backstory_parts[0]:
            backstory_hint = f" I'm {backstory_parts[0]}."
        else:
            backstory_hint = f" I'm {npc_data['backstory']}."
        
        return base_greeting + modifier + backstory_hint
    
    def generate_greeting(self, npc_data, archetype, disposition):
        """Generate greeting based on relationship"""
        if disposition > 70:
            greeting_options = ['How can I help?', 'What brings you here?', 'Always a pleasure!']
            return f"Ah, my friend! Good to see you again. {random.choice(greeting_options)}"
        elif disposition > 40:
            greetings = archetype.get('greetings', ["Hello."])
            return random.choice(greetings)
        else:
            rude_options = ['What do you want?', 'Make it quick.', 'I\'m busy.']
            return f"Oh, it's you. {random.choice(rude_options)}"
    
    def generate_threat_response(self, npc_data, disposition):
        """Generate response to threats"""
        if npc_data['type'] == 'guard':
            return "You dare threaten a guard? You'll regret this!"
        elif disposition < 30:
            return "P-please! I don't want any trouble! Take what you want!"
        elif npc_data['personality'] == 'arrogant':
            return "Ha! You think you can threaten ME? How amusing."
        else:
            return "Back off! I'm warning you!"
    
    def generate_compliment_response(self, npc_data):
        """Generate response to compliments"""
        responses = {
            "friendly": "Oh, how kind of you to say! You've made my day!",
            "suspicious": "Flattery? What are you after?",
            "arrogant": "Well, of course. I'm glad you noticed.",
            "nervous": "Oh! Um, th-thank you... that's very nice...",
            "wise": "Kind words cost nothing but mean everything."
        }
        return responses.get(npc_data['personality'], "Thank you, that's very kind.")
    
    def generate_quest_dialogue(self, npc_data, context):
        """Generate quest-related dialogue"""
        if npc_data['type'] != 'questgiver':
            return f"I'm just a {npc_data['type']}, I don't have any quests for you."
        
        if npc_data['disposition'] < 30:
            return "I wouldn't trust you with my problems."
        
        quests = [
            "There's been strange activity in the old ruins to the north...",
            "Bandits have been terrorizing travelers on the eastern road.",
            "I lost a precious family heirloom in the dark forest.",
            "The town well has been poisoned - we need the antidote from the swamp witch.",
            "An ancient evil stirs in the abandoned mine shaft."
        ]
        
        return random.choice(quests) + " Will you help?"
    
    def generate_trade_dialogue(self, npc_data):
        """Generate trade dialogue"""
        if npc_data['type'] != 'merchant':
            return "I'm not a merchant, but you might try the market square."
        
        if npc_data['disposition'] > 60:
            return "For you, my friend, special prices! Take a look at my wares."
        else:
            return "Certainly, have a look at what I'm selling. Standard prices, of course."
    
    def generate_contextual_dialogue(self, npc_data, player_action, context):
        """Generate dialogue based on specific context"""
        time_of_day = context.get('time_of_day', 12)
        weather = context.get('weather', 'clear')
        location = context.get('location', 'town')
        
        # Time-based responses
        if time_of_day < 6 or time_of_day > 22:
            if npc_data['type'] == 'guard':
                return "It's late. You should find shelter for the night."
            else:
                return "What are you doing out at this hour?"
        
        # Weather-based responses
        if weather == 'rain':
            return random.choice([
                "Terrible weather we're having.",
                "This rain is good for the crops, at least.",
                "I hope this rain ends soon."
            ])
        
        # Location-based responses
        if location == 'dungeon':
            return "What are we doing in this forsaken place?!"
        
        # Default contextual response
        if npc_data['secrets']:
            if npc_data['disposition'] > 70:
                return f"Can I trust you with something? {npc_data['secrets']}"
        
        return "Is there something else you need?"
    
    def generate_response_options(self, npc_data, context):
        """Generate dialogue options for the player"""
        options = ["Goodbye", "Tell me about yourself", "Do you have any work for me?"]
        
        if npc_data['type'] == 'merchant':
            options.append("I'd like to trade")
        
        if npc_data['type'] == 'guard':
            options.append("What's the news?")
            options.append("I want to report a crime")
        
        if npc_data['type'] == 'innkeeper':
            options.append("I need a room")
            options.append("Any rumors?")
        
        if npc_data['disposition'] > 60:
            options.append("Can you teach me anything?")
        
        if npc_data['secrets'] and npc_data['disposition'] > 70:
            options.append("Tell me your secret")
        
        return options
    
    def generate_quest_offer(self, npc_data, context):
        """Generate a procedural quest offer"""
        quest_types = [
            {"type": "fetch", "target": "ancient_artifact", "location": "ruins", "reward": 500},
            {"type": "kill", "target": "bandit_leader", "location": "camp", "reward": 750},
            {"type": "escort", "target": "merchant", "location": "next_town", "reward": 300},
            {"type": "investigate", "target": "disappearances", "location": "village", "reward": 400},
            {"type": "deliver", "target": "message", "location": "castle", "reward": 200}
        ]
        
        quest = random.choice(quest_types)
        quest['giver'] = npc_data['name']
        quest['id'] = f"quest_{npc_data['name']}_{context.get('day_count', 1)}"
        
        return quest
    
    def determine_emotion(self, personality, disposition, player_action):
        """Determine NPC's emotional state"""
        if player_action == "threaten":
            return "afraid" if personality == "nervous" else "angry"
        elif player_action == "compliment":
            return "happy" if personality == "friendly" else "suspicious" if personality == "suspicious" else "pleased"
        elif disposition > 70:
            return "friendly"
        elif disposition < 30:
            return "hostile"
        else:
            return "neutral"
    
    def update_npc_memory(self, npc_name, player_action, dialogue_response):
        """Update NPC's memory of interactions"""
        memory_data = self.storage_manager.read_json()
        npcs = memory_data.get('npcs', {})
        
        if npc_name in npcs:
            npc_data = npcs[npc_name]
            
            # Safely get dialogue string
            dialogue_text = dialogue_response.get('dialogue', '')
            if dialogue_text:
                dialogue_text = dialogue_text[:100]  # Store first 100 chars
            
            memory_entry = {
                "action": player_action,
                "response": dialogue_text,
                "emotion": dialogue_response.get('emotion', 'neutral'),
                "timestamp": str(datetime.now())
            }
            
            memories = npc_data.get('memories', [])
            memories.append(memory_entry)
            
            # Keep only last 10 memories
            npc_data['memories'] = memories[-10:]
            
            npcs[npc_name] = npc_data
            memory_data['npcs'] = npcs
            self.storage_manager.write_json(memory_data)
    
    def generate_npc_name(self):
        """Generate a random NPC name"""
        first_names = ["Aldric", "Bella", "Cedric", "Diana", "Edmund", "Fiona", "Gareth", "Helena", "Ivan", "Julia"]
        last_names = ["Blackwood", "Riverstone", "Goldleaf", "Ironforge", "Windwalker", "Moonshire", "Starweaver"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def generate_backstory(self, npc_type):
        """Generate a backstory for the NPC"""
        backstories = {
            "merchant": [
                "a third-generation trader from a long line of merchants",
                "a former adventurer who settled down to sell exotic goods",
                "a refugee who rebuilt their life through honest trade"
            ],
            "guard": [
                "a veteran of the kingdom's army, now keeping the peace",
                "a young recruit eager to prove themselves",
                "a reformed criminal who now upholds the law"
            ],
            "questgiver": [
                "a retired hero with unfinished business",
                "a scholar researching ancient mysteries",
                "a noble seeking help for their troubled lands"
            ],
            "innkeeper": [
                "a former bard who settled down to run this establishment",
                "the inheritor of a family business spanning generations",
                "a worldly traveler who decided to create a home for others"
            ],
            "wizard": [
                "a student of the arcane arts for over a century",
                "an exile from the mage's college seeking redemption",
                "a self-taught prodigy with unconventional methods"
            ]
        }
        
        type_stories = backstories.get(npc_type, ["a simple villager living their life"])
        return random.choice(type_stories)
    
    def generate_npc_inventory(self, npc_type):
        """Generate items the NPC might have"""
        inventories = {
            "merchant": ["health_potion", "rope", "torch", "map", "rare_gem"],
            "guard": ["sword", "shield", "arrest_warrant", "keys"],
            "innkeeper": ["ale", "bread", "room_key", "gossip_journal"],
            "wizard": ["spell_scroll", "magic_crystal", "ancient_tome", "potion_ingredients"]
        }
        
        return inventories.get(npc_type, ["coin_purse"])
    
    def generate_secrets(self, npc_type):
        """Generate a secret the NPC might have"""
        secrets = [
            "I saw strange lights in the forest last night",
            "The mayor isn't who they claim to be",
            "There's a hidden treasure in the old well",
            "I know where the bandits hide their loot",
            "The blacksmith is secretly a wizard",
            "Something evil lurks in the castle basement",
            "I witnessed a murder but I'm too scared to report it"
        ]
        
        return random.choice(secrets)