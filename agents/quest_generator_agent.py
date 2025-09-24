import json
import random
import logging
from datetime import datetime
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class QuestGeneratorAgent(BasicAgent):
    def __init__(self):
        self.name = 'QuestGenerator'
        self.metadata = {
            "name": self.name,
            "description": "Generates dynamic, contextual quests based on player actions, world state, and narrative progression",
            "parameters": {
                "type": "object",
                "properties": {
                    "quest_type": {
                        "type": "string",
                        "description": "Type of quest to generate (main, side, random)",
                        "enum": ["main", "side", "random", "chain", "emergent"]
                    },
                    "context": {
                        "type": "object",
                        "description": "Context including player level, location, faction standings"
                    },
                    "trigger": {
                        "type": "string",
                        "description": "What triggered this quest (npc_interaction, world_event, player_action)"
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for personalized quest generation"
                    }
                },
                "required": ["quest_type"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)
        
        # Quest templates
        self.quest_templates = {
            "fetch": {
                "objectives": ["retrieve", "collect", "gather", "find"],
                "targets": ["artifact", "herbs", "ore", "scroll", "gem"],
                "locations": ["ancient_ruins", "dark_forest", "abandoned_mine", "mystic_cave"]
            },
            "kill": {
                "objectives": ["defeat", "eliminate", "destroy", "vanquish"],
                "targets": ["bandit_leader", "monster", "corrupt_official", "dark_wizard"],
                "locations": ["enemy_camp", "dungeon", "fortress", "lair"]
            },
            "escort": {
                "objectives": ["protect", "guide", "accompany", "deliver"],
                "targets": ["merchant", "noble", "scholar", "refugee"],
                "locations": ["neighboring_town", "capital", "border", "safe_house"]
            },
            "investigate": {
                "objectives": ["uncover", "discover", "solve", "explore"],
                "targets": ["mystery", "disappearances", "conspiracy", "phenomena"],
                "locations": ["crime_scene", "library", "tavern", "underground"]
            }
        }
    
    def perform(self, **kwargs):
        quest_type = kwargs.get('quest_type', 'random')
        context = kwargs.get('context', {})
        trigger = kwargs.get('trigger', 'random')
        user_guid = kwargs.get('user_guid')
        
        if user_guid:
            self.storage_manager.set_memory_context(user_guid)
        
        # Get player quest history
        quest_history = self.get_quest_history()
        
        # Generate quest based on type
        if quest_type == "main":
            quest = self.generate_main_quest(context, quest_history)
        elif quest_type == "side":
            quest = self.generate_side_quest(context, trigger)
        elif quest_type == "chain":
            quest = self.generate_chain_quest(quest_history)
        elif quest_type == "emergent":
            quest = self.generate_emergent_quest(context, trigger)
        else:
            quest = self.generate_random_quest(context)
        
        # Save quest to memory
        self.save_quest(quest)
        
        return json.dumps({
            "status": "success",
            "quest": quest,
            "narrative": quest['narrative'],
            "objectives": quest['objectives'],
            "rewards": quest['rewards']
        })
    
    def generate_main_quest(self, context, quest_history):
        """Generate a main story quest"""
        chapter = len([q for q in quest_history if q.get('type') == 'main']) + 1
        
        main_quest_arc = [
            {
                "title": "The Awakening",
                "narrative": "Ancient forces stir. A prophecy speaks of a chosen hero...",
                "objectives": [
                    {"description": "Speak with the Elder Sage", "type": "dialogue"},
                    {"description": "Retrieve the Prophecy Scroll", "type": "fetch"},
                    {"description": "Activate the Ancient Beacon", "type": "interact"}
                ]
            },
            {
                "title": "Gathering Allies",
                "narrative": "The darkness grows. You must unite the fractured kingdoms...",
                "objectives": [
                    {"description": "Gain favor with three factions", "type": "reputation"},
                    {"description": "Recruit a legendary warrior", "type": "recruit"},
                    {"description": "Forge an alliance treaty", "type": "diplomacy"}
                ]
            },
            {
                "title": "The First Trial",
                "narrative": "To prove your worth, you must face the Trial of Elements...",
                "objectives": [
                    {"description": "Defeat the Fire Guardian", "type": "boss"},
                    {"description": "Solve the Water Temple puzzle", "type": "puzzle"},
                    {"description": "Survive the Earth Labyrinth", "type": "survival"}
                ]
            },
            {
                "title": "The Shadow Rises",
                "narrative": "The enemy reveals itself. War comes to the realm...",
                "objectives": [
                    {"description": "Defend the capital from invasion", "type": "defense"},
                    {"description": "Infiltrate the enemy stronghold", "type": "stealth"},
                    {"description": "Discover the enemy's true identity", "type": "investigate"}
                ]
            },
            {
                "title": "The Final Battle",
                "narrative": "All paths lead here. The fate of the world hangs in balance...",
                "objectives": [
                    {"description": "Gather the legendary artifacts", "type": "collect"},
                    {"description": "Rally your allies for battle", "type": "preparation"},
                    {"description": "Defeat the Ancient Evil", "type": "final_boss"}
                ]
            }
        ]
        
        quest_data = main_quest_arc[min(chapter - 1, len(main_quest_arc) - 1)]
        
        return {
            "id": f"main_quest_chapter_{chapter}",
            "type": "main",
            "chapter": chapter,
            "title": quest_data['title'],
            "narrative": quest_data['narrative'],
            "objectives": quest_data['objectives'],
            "rewards": {
                "experience": 1000 * chapter,
                "gold": 500 * chapter,
                "items": [f"legendary_item_tier_{chapter}"],
                "story_progression": True
            },
            "level_requirement": chapter * 10,
            "time_limit": None,
            "consequences": {
                "success": f"Chapter {chapter + 1} unlocked",
                "failure": "The darkness grows stronger"
            }
        }
    
    def generate_side_quest(self, context, trigger):
        """Generate a side quest based on trigger"""
        player_level = context.get('player_level', 1)
        location = context.get('location', 'town')
        faction = context.get('dominant_faction', 'neutral')
        
        side_quests = {
            "npc_interaction": [
                {
                    "title": "A Friend in Need",
                    "narrative": "An old friend needs help with a personal matter",
                    "objective_type": "fetch",
                    "difficulty": "easy"
                },
                {
                    "title": "Family Secrets",
                    "narrative": "Uncover the truth behind a family's dark past",
                    "objective_type": "investigate",
                    "difficulty": "medium"
                }
            ],
            "world_event": [
                {
                    "title": "Crisis Response",
                    "narrative": "The recent events have created chaos that needs addressing",
                    "objective_type": "kill",
                    "difficulty": "hard"
                },
                {
                    "title": "Opportunity Knocks",
                    "narrative": "The chaos has revealed hidden opportunities",
                    "objective_type": "fetch",
                    "difficulty": "medium"
                }
            ],
            "player_action": [
                {
                    "title": "Consequences",
                    "narrative": "Your recent actions have attracted attention",
                    "objective_type": "escort",
                    "difficulty": "medium"
                },
                {
                    "title": "Reputation Matters",
                    "narrative": "Someone has heard of your deeds and needs help",
                    "objective_type": "investigate",
                    "difficulty": "easy"
                }
            ]
        }
        
        quest_pool = side_quests.get(trigger, side_quests['player_action'])
        quest_template = random.choice(quest_pool)
        
        # Generate specific objectives based on template
        objective_type = quest_template['objective_type']
        objectives = self.generate_objectives(objective_type, quest_template['difficulty'])
        
        return {
            "id": f"side_{trigger}_{datetime.now().timestamp()}",
            "type": "side",
            "title": quest_template['title'],
            "narrative": quest_template['narrative'],
            "objectives": objectives,
            "rewards": self.calculate_rewards(player_level, quest_template['difficulty']),
            "level_requirement": max(1, player_level - 5),
            "time_limit": random.choice([None, "3_days", "1_week"]),
            "faction_impact": {faction: random.randint(-10, 10)}
        }
    
    def generate_chain_quest(self, quest_history):
        """Generate a quest that continues from a previous quest"""
        # Find completed quests that can have follow-ups
        completed_quests = [q for q in quest_history if q.get('status') == 'completed']
        
        if not completed_quests:
            return self.generate_random_quest({})
        
        parent_quest = random.choice(completed_quests[-5:])  # Recent quests only
        
        chain_templates = [
            {
                "title": f"Aftermath of {parent_quest.get('title', 'Previous Quest')}",
                "narrative": "Your previous actions have had unexpected consequences",
                "objectives": [
                    {"description": "Deal with the unintended results", "type": "investigate"},
                    {"description": "Fix what was broken", "type": "repair"}
                ]
            },
            {
                "title": f"The Truth Behind {parent_quest.get('title', 'Previous Quest')}",
                "narrative": "New information has come to light about your previous quest",
                "objectives": [
                    {"description": "Uncover the hidden truth", "type": "investigate"},
                    {"description": "Confront the real culprit", "type": "confrontation"}
                ]
            }
        ]
        
        template = random.choice(chain_templates)
        
        return {
            "id": f"chain_{parent_quest.get('id', 'unknown')}_{datetime.now().timestamp()}",
            "type": "chain",
            "parent_quest": parent_quest.get('id'),
            "title": template['title'],
            "narrative": template['narrative'],
            "objectives": template['objectives'],
            "rewards": {
                "experience": parent_quest.get('rewards', {}).get('experience', 100) * 1.5,
                "gold": parent_quest.get('rewards', {}).get('gold', 50) * 1.2,
                "items": ["continuation_reward"],
                "story_revelation": True
            }
        }
    
    def generate_emergent_quest(self, context, trigger):
        """Generate quest based on emergent gameplay situations"""
        world_state = context.get('world_state', {})
        player_actions = context.get('recent_actions', [])
        
        emergent_scenarios = []
        
        # Check world threats
        if world_state.get('world_threats'):
            emergent_scenarios.append({
                "title": "Clear and Present Danger",
                "narrative": f"The {world_state['world_threats'][0]} threatens everyone",
                "objectives": [
                    {"description": "Investigate the threat", "type": "investigate"},
                    {"description": "Neutralize the danger", "type": "combat"}
                ],
                "urgency": "high"
            })
        
        # Check faction conflicts
        faction_standings = world_state.get('faction_standings', {})
        hostile_factions = [f for f, standing in faction_standings.items() if standing < 20]
        if hostile_factions:
            emergent_scenarios.append({
                "title": "Diplomatic Solution",
                "narrative": f"Your conflict with {hostile_factions[0]} escalates",
                "objectives": [
                    {"description": "Negotiate a truce", "type": "diplomacy"},
                    {"description": "Or eliminate their leader", "type": "assassination"}
                ],
                "urgency": "medium"
            })
        
        # Player crime/heroics
        if "steal" in player_actions:
            emergent_scenarios.append({
                "title": "The Long Arm of the Law",
                "narrative": "Your crimes have caught up with you",
                "objectives": [
                    {"description": "Evade capture", "type": "escape"},
                    {"description": "Clear your name", "type": "investigate"}
                ],
                "urgency": "high"
            })
        
        if emergent_scenarios:
            scenario = random.choice(emergent_scenarios)
            return {
                "id": f"emergent_{trigger}_{datetime.now().timestamp()}",
                "type": "emergent",
                "title": scenario['title'],
                "narrative": scenario['narrative'],
                "objectives": scenario['objectives'],
                "rewards": {
                    "experience": 500,
                    "reputation_change": True,
                    "unique_outcome": True
                },
                "urgency": scenario['urgency'],
                "auto_fail_time": "24_hours" if scenario['urgency'] == 'high' else None
            }
        
        return self.generate_random_quest(context)
    
    def generate_random_quest(self, context):
        """Generate a completely random quest"""
        quest_type = random.choice(list(self.quest_templates.keys()))
        template = self.quest_templates[quest_type]
        
        objective = random.choice(template['objectives'])
        target = random.choice(template['targets'])
        location = random.choice(template['locations'])
        
        title_formats = [
            f"The {target.replace('_', ' ').title()} of {location.replace('_', ' ').title()}",
            f"{objective.title()} the {target.replace('_', ' ').title()}",
            f"Trouble at {location.replace('_', ' ').title()}"
        ]
        
        return {
            "id": f"random_{datetime.now().timestamp()}",
            "type": "random",
            "title": random.choice(title_formats),
            "narrative": f"You must {objective} the {target} at {location}",
            "objectives": [
                {
                    "description": f"{objective.title()} the {target.replace('_', ' ')}",
                    "type": quest_type,
                    "target": target,
                    "location": location,
                    "count": random.randint(1, 5) if quest_type == "fetch" else 1
                }
            ],
            "rewards": {
                "experience": random.randint(50, 200),
                "gold": random.randint(20, 100),
                "items": ["random_loot"]
            },
            "difficulty": random.choice(["easy", "medium", "hard"]),
            "optional": True
        }
    
    def generate_objectives(self, objective_type, difficulty):
        """Generate specific objectives based on type and difficulty"""
        objective_count = {"easy": 1, "medium": 2, "hard": 3}[difficulty]
        objectives = []
        
        for i in range(objective_count):
            if objective_type == "fetch":
                objectives.append({
                    "description": f"Collect {random.randint(3, 10)} rare items",
                    "type": "collect",
                    "progress": 0
                })
            elif objective_type == "kill":
                objectives.append({
                    "description": f"Defeat {random.randint(5, 15)} enemies",
                    "type": "combat",
                    "progress": 0
                })
            elif objective_type == "investigate":
                objectives.append({
                    "description": "Find clues about the mystery",
                    "type": "explore",
                    "progress": 0
                })
            elif objective_type == "escort":
                objectives.append({
                    "description": "Safely escort the target",
                    "type": "protect",
                    "progress": 0
                })
        
        return objectives
    
    def calculate_rewards(self, player_level, difficulty):
        """Calculate appropriate rewards based on level and difficulty"""
        base_exp = player_level * 10
        base_gold = player_level * 5
        
        multipliers = {"easy": 1, "medium": 1.5, "hard": 2}
        multiplier = multipliers[difficulty]
        
        return {
            "experience": int(base_exp * multiplier),
            "gold": int(base_gold * multiplier),
            "items": [f"{difficulty}_reward_item"],
            "reputation": random.randint(1, 10) * multiplier
        }
    
    def get_quest_history(self):
        """Get player's quest history from memory"""
        memory_data = self.storage_manager.read_json()
        return memory_data.get('quest_history', [])
    
    def save_quest(self, quest):
        """Save quest to player's active quests"""
        memory_data = self.storage_manager.read_json()
        active_quests = memory_data.get('active_quests', [])
        
        # Add timestamp
        quest['received_at'] = str(datetime.now())
        quest['status'] = 'active'
        
        active_quests.append(quest)
        memory_data['active_quests'] = active_quests
        
        self.storage_manager.write_json(memory_data)