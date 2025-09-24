import json
import random
import logging
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager

class CombatNarratorAgent(BasicAgent):
    def __init__(self):
        self.name = 'CombatNarrator'
        self.metadata = {
            "name": self.name,
            "description": "Provides dynamic narrative descriptions for combat encounters, making battles feel cinematic and impactful",
            "parameters": {
                "type": "object",
                "properties": {
                    "combat_event": {
                        "type": "string",
                        "description": "Type of combat event",
                        "enum": ["attack", "defend", "critical", "miss", "death", "victory", "special_move", "environmental"]
                    },
                    "attacker": {
                        "type": "object",
                        "description": "Attacker information"
                    },
                    "defender": {
                        "type": "object",
                        "description": "Defender information"
                    },
                    "damage": {
                        "type": "number",
                        "description": "Damage dealt"
                    },
                    "context": {
                        "type": "object",
                        "description": "Combat context (environment, weather, etc.)"
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for personalized combat narration"
                    }
                },
                "required": ["combat_event"]
            }
        }
        self.storage_manager = AzureFileStorageManager()
        super().__init__(name=self.name, metadata=self.metadata)
        
        # Combat narration styles
        self.narration_styles = ["epic", "brutal", "tactical", "dramatic", "humorous"]
    
    def perform(self, **kwargs):
        combat_event = kwargs.get('combat_event')
        attacker = kwargs.get('attacker', {})
        defender = kwargs.get('defender', {})
        damage = kwargs.get('damage', 0)
        context = kwargs.get('context', {})
        user_guid = kwargs.get('user_guid')
        
        if user_guid:
            self.storage_manager.set_memory_context(user_guid)
        
        # Get combat style preference
        combat_style = self.get_combat_style()
        
        # Generate narration based on event
        if combat_event == "attack":
            narration = self.narrate_attack(attacker, defender, damage, combat_style, context)
        elif combat_event == "defend":
            narration = self.narrate_defense(attacker, defender, combat_style)
        elif combat_event == "critical":
            narration = self.narrate_critical(attacker, defender, damage, combat_style)
        elif combat_event == "miss":
            narration = self.narrate_miss(attacker, defender, combat_style)
        elif combat_event == "death":
            narration = self.narrate_death(defender, combat_style)
        elif combat_event == "victory":
            narration = self.narrate_victory(attacker, defender, combat_style)
        elif combat_event == "special_move":
            narration = self.narrate_special_move(attacker, defender, damage, combat_style)
        elif combat_event == "environmental":
            narration = self.narrate_environmental(context, combat_style)
        else:
            narration = self.generate_generic_combat_text(combat_event, combat_style)
        
        # Add combat tips or flavor
        combat_insight = self.generate_combat_insight(combat_event, context)
        
        # Update combat statistics
        self.update_combat_stats(combat_event, damage)
        
        return json.dumps({
            "status": "success",
            "narration": narration,
            "combat_insight": combat_insight,
            "style": combat_style,
            "dramatic_pause": self.should_dramatic_pause(combat_event),
            "camera_shake": damage > 20,
            "special_effect": self.get_special_effect(combat_event)
        })
    
    def get_combat_style(self):
        """Get player's preferred combat narration style"""
        memory_data = self.storage_manager.read_json()
        preferences = memory_data.get('preferences', {})
        return preferences.get('combat_style', random.choice(self.narration_styles))
    
    def narrate_attack(self, attacker, defender, damage, style, context):
        """Generate attack narration"""
        weapon = attacker.get('weapon', 'sword')
        attacker_name = attacker.get('name', 'The attacker')
        defender_name = defender.get('name', 'the defender')
        
        narrations = {
            "epic": [
                f"{attacker_name}'s {weapon} sings through the air, finding its mark for {damage} damage!",
                f"With legendary skill, {attacker_name} strikes {defender_name} for {damage} damage!",
                f"The battle rages as {attacker_name} lands a decisive blow for {damage} damage!"
            ],
            "brutal": [
                f"{attacker_name} savagely attacks with their {weapon}, dealing {damage} damage!",
                f"Blood sprays as {attacker_name}'s {weapon} tears into {defender_name} for {damage} damage!",
                f"{attacker_name} shows no mercy, inflicting {damage} damage!"
            ],
            "tactical": [
                f"{attacker_name} exploits an opening, dealing {damage} damage with their {weapon}.",
                f"Calculated strike: {attacker_name} hits {defender_name} for {damage} damage.",
                f"Precision attack lands for {damage} damage."
            ],
            "dramatic": [
                f"Time slows as {attacker_name}'s {weapon} connects, dealing {damage} damage!",
                f"The clash of steel! {attacker_name} strikes for {damage} damage!",
                f"Destiny unfolds as {attacker_name} wounds {defender_name} for {damage} damage!"
            ],
            "humorous": [
                f"{attacker_name} bonks {defender_name} for {damage} damage. Ouch!",
                f"That's gotta hurt! {damage} damage from {attacker_name}!",
                f"{defender_name} definitely felt that one - {damage} damage!"
            ]
        }
        
        style_narrations = narrations.get(style, narrations['epic'])
        base_narration = random.choice(style_narrations)
        
        # Add environmental flavor
        if context.get('weather') == 'rain':
            base_narration += " Rain streams down the combatants."
        elif context.get('location') == 'dungeon':
            base_narration += " Echoes fill the dark corridors."
        
        return base_narration
    
    def narrate_defense(self, attacker, defender, style):
        """Generate defense narration"""
        defender_name = defender.get('name', 'The defender')
        
        narrations = {
            "epic": f"{defender_name} heroically blocks the attack!",
            "brutal": f"{defender_name} barely deflects the savage blow!",
            "tactical": f"{defender_name} anticipates and counters the attack.",
            "dramatic": f"Against all odds, {defender_name} stands firm!",
            "humorous": f"{defender_name} says 'Not today!' and blocks!"
        }
        
        return narrations.get(style, narrations['epic'])
    
    def narrate_critical(self, attacker, defender, damage, style):
        """Generate critical hit narration"""
        attacker_name = attacker.get('name', 'The attacker')
        
        narrations = {
            "epic": f"CRITICAL STRIKE! {attacker_name} unleashes devastating power for {damage} damage!",
            "brutal": f"CRUSHING BLOW! {attacker_name} deals {damage} damage in a spray of blood!",
            "tactical": f"WEAK POINT EXPLOITED! {attacker_name} deals {damage} critical damage!",
            "dramatic": f"THE FATES ALIGN! {attacker_name}'s critical hit deals {damage} damage!",
            "humorous": f"BOOM! HEADSHOT! {damage} critical damage! That's a lot of damage!"
        }
        
        return narrations.get(style, narrations['epic'])
    
    def narrate_miss(self, attacker, defender, style):
        """Generate miss narration"""
        attacker_name = attacker.get('name', 'The attacker')
        defender_name = defender.get('name', 'the defender')
        
        narrations = {
            "epic": f"{attacker_name}'s attack whistles past {defender_name}!",
            "brutal": f"{attacker_name} swings wildly and misses!",
            "tactical": f"{defender_name} evades {attacker_name}'s calculated strike.",
            "dramatic": f"Fate intervenes! The attack misses by a hair's breadth!",
            "humorous": f"Whoosh! {attacker_name} hits nothing but air!"
        }
        
        return narrations.get(style, narrations['epic'])
    
    def narrate_death(self, defender, style):
        """Generate death narration"""
        defender_name = defender.get('name', 'The defender')
        
        narrations = {
            "epic": f"{defender_name} falls in glorious battle! Their legend will be remembered!",
            "brutal": f"{defender_name} collapses in a pool of blood. The battle is won.",
            "tactical": f"Target eliminated. {defender_name} has been neutralized.",
            "dramatic": f"With a final breath, {defender_name} falls. The battlefield grows quiet.",
            "humorous": f"{defender_name} has left the chat. Permanently."
        }
        
        return narrations.get(style, narrations['epic'])
    
    def narrate_victory(self, attacker, defender, style):
        """Generate victory narration"""
        attacker_name = attacker.get('name', 'The victor')
        
        narrations = {
            "epic": f"{attacker_name} stands victorious! Songs will be sung of this triumph!",
            "brutal": f"{attacker_name} stands over their fallen foe, victorious and bloodied!",
            "tactical": f"Mission accomplished. {attacker_name} has achieved victory.",
            "dramatic": f"Against all odds, {attacker_name} emerges victorious!",
            "humorous": f"{attacker_name} wins! Time for the victory dance!"
        }
        
        return narrations.get(style, narrations['epic'])
    
    def narrate_special_move(self, attacker, defender, damage, style):
        """Generate special move narration"""
        move_name = attacker.get('special_move', 'special attack')
        attacker_name = attacker.get('name', 'The attacker')
        
        narrations = {
            "epic": f"{attacker_name} unleashes {move_name}! The very earth trembles! {damage} damage!",
            "brutal": f"{attacker_name}'s {move_name} tears through everything! {damage} damage!",
            "tactical": f"Special technique deployed: {move_name}. Damage: {damage}.",
            "dramatic": f"Power surges as {attacker_name} releases {move_name}! {damage} damage!",
            "humorous": f"{attacker_name} goes SUPER SAIYAN with {move_name}! It's over {damage}!"
        }
        
        return narrations.get(style, narrations['epic'])
    
    def narrate_environmental(self, context, style):
        """Generate environmental combat effect narration"""
        effect = context.get('effect', 'environmental hazard')
        
        narrations = {
            "epic": f"The battlefield itself joins the fight! {effect} affects all combatants!",
            "brutal": f"Nature shows no mercy! {effect} ravages the battlefield!",
            "tactical": f"Environmental factor: {effect} now in play.",
            "dramatic": f"The very elements conspire! {effect} changes everything!",
            "humorous": f"Mother Nature enters the chat with {effect}!"
        }
        
        return narrations.get(style, narrations['epic'])
    
    def generate_combat_insight(self, combat_event, context):
        """Generate tactical insights or tips"""
        insights = {
            "attack": [
                "Timing your attacks can increase critical chance.",
                "Different weapons work better against different armor types.",
                "Combos deal increasing damage."
            ],
            "defend": [
                "Perfect blocks can stun your opponent.",
                "Defense reduces damage but costs stamina.",
                "Some attacks cannot be blocked."
            ],
            "critical": [
                "Critical strikes ignore armor.",
                "Backstabs have increased critical chance.",
                "Some skills increase critical damage."
            ],
            "miss": [
                "Accuracy decreases with fatigue.",
                "Weather affects hit chance.",
                "Agility improves evasion."
            ]
        }
        
        event_insights = insights.get(combat_event, ["Combat is unpredictable."])
        return random.choice(event_insights)
    
    def should_dramatic_pause(self, combat_event):
        """Determine if this moment needs a dramatic pause"""
        dramatic_events = ["critical", "death", "victory", "special_move"]
        return combat_event in dramatic_events
    
    def get_special_effect(self, combat_event):
        """Get special visual/audio effect for the event"""
        effects = {
            "critical": "screen_flash_red",
            "death": "slow_motion",
            "victory": "victory_fanfare",
            "special_move": "power_aura",
            "environmental": "weather_intensify"
        }
        return effects.get(combat_event, None)
    
    def update_combat_stats(self, combat_event, damage):
        """Track combat statistics"""
        memory_data = self.storage_manager.read_json()
        combat_stats = memory_data.get('combat_stats', {
            'total_damage_dealt': 0,
            'total_damage_taken': 0,
            'critical_hits': 0,
            'misses': 0,
            'victories': 0,
            'defeats': 0,
            'special_moves_used': 0
        })
        
        if combat_event == "attack":
            combat_stats['total_damage_dealt'] += damage
        elif combat_event == "critical":
            combat_stats['critical_hits'] += 1
            combat_stats['total_damage_dealt'] += damage
        elif combat_event == "miss":
            combat_stats['misses'] += 1
        elif combat_event == "victory":
            combat_stats['victories'] += 1
        elif combat_event == "death":
            combat_stats['defeats'] += 1
        elif combat_event == "special_move":
            combat_stats['special_moves_used'] += 1
            combat_stats['total_damage_dealt'] += damage
        
        memory_data['combat_stats'] = combat_stats
        self.storage_manager.write_json(memory_data)
    
    def generate_generic_combat_text(self, event, style):
        """Fallback for unknown combat events"""
        return f"The battle continues with {event}!"