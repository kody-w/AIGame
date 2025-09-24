import azure.functions as func
import logging
import json
import os
import importlib
import importlib.util
import inspect
import sys
import re
from agents.basic_agent import BasicAgent
import uuid
from openai import AzureOpenAI
from datetime import datetime
import time
from utils.azure_file_storage import AzureFileStorageManager, safe_json_loads

# Default GUID to use when no specific user GUID is provided
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

def ensure_string_content(message):
    """
    Ensures message content is converted to a string regardless of input type.
    Handles all edge cases including None, undefined, or missing content.
    """
    if message is None:
        return {"role": "user", "content": ""}
        
    if not isinstance(message, dict):
        return {"role": "user", "content": str(message) if message is not None else ""}
    
    message = message.copy()
    
    if 'role' not in message:
        message['role'] = 'user'
    
    if 'content' in message:
        content = message['content']
        message['content'] = str(content) if content is not None else ''
    else:
        message['content'] = ''
    
    return message

def ensure_string_function_args(function_call):
    """
    Ensures function call arguments are properly stringified.
    Handles None and edge cases.
    """
    if not function_call:
        return None
    
    if not hasattr(function_call, 'arguments'):
        return None
        
    if function_call.arguments is None:
        return None
        
    if isinstance(function_call.arguments, (dict, list)):
        return json.dumps(function_call.arguments)
    
    return str(function_call.arguments)

def build_cors_response(origin):
    """
    Builds CORS response headers.
    Safely handles None origin.
    """
    return {
        "Access-Control-Allow-Origin": str(origin) if origin else "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400",
    }

def load_agents_from_folder():
    agents_directory = os.path.join(os.path.dirname(__file__), "agents")
    files_in_agents_directory = os.listdir(agents_directory)
    agent_files = [f for f in files_in_agents_directory if f.endswith(".py") and f not in ["__init__.py", "basic_agent.py"]]

    declared_agents = {}
    for file in agent_files:
        try:
            module_name = file[:-3]
            module = importlib.import_module(f'agents.{module_name}')
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasicAgent) and obj is not BasicAgent:
                    agent_instance = obj()
                    declared_agents[agent_instance.name] = agent_instance
        except Exception as e:
            logging.error(f"Error loading agent {file}: {str(e)}")
            continue

    storage_manager = AzureFileStorageManager()
    try:
        agent_files = storage_manager.list_files('agents')
        
        for file in agent_files:
            if not file.name.endswith('_agent.py'):
                continue

            try:
                file_content = storage_manager.read_file('agents', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/agents"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = f"{temp_dir}/{file.name}"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.append(temp_dir)

                module_name = file.name[:-3]
                spec = importlib.util.spec_from_file_location(module_name, temp_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BasicAgent) and
                        obj is not BasicAgent):
                        agent_instance = obj()
                        declared_agents[agent_instance.name] = agent_instance

                os.remove(temp_file)

            except Exception as e:
                logging.error(f"Error loading agent {file.name} from Azure File Share: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error loading agents from Azure File Share: {str(e)}")

    # Load multi-agents from multi_agents folder
    try:
        multi_agent_files = storage_manager.list_files('multi_agents')
        
        for file in multi_agent_files:
            if not file.name.endswith('_agent.py'):
                continue

            try:
                file_content = storage_manager.read_file('multi_agents', file.name)
                if file_content is None:
                    continue

                temp_dir = "/tmp/multi_agents"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = f"{temp_dir}/{file.name}"

                with open(temp_file, 'w') as f:
                    f.write(file_content)

                if temp_dir not in sys.path:
                    sys.path.append(temp_dir)

                parent_dir = "/tmp"
                if parent_dir not in sys.path:
                    sys.path.append(parent_dir)

                module_name = file.name[:-3]
                spec = importlib.util.spec_from_file_location(f"multi_agents.{module_name}", temp_file)
                module = importlib.util.module_from_spec(spec)
                
                import types
                if 'multi_agents' not in sys.modules:
                    multi_agents_module = types.ModuleType('multi_agents')
                    sys.modules['multi_agents'] = multi_agents_module
                
                sys.modules[f"multi_agents.{module_name}"] = module
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BasicAgent) and
                        obj is not BasicAgent):
                        agent_instance = obj()
                        declared_agents[agent_instance.name] = agent_instance
                        logging.info(f"Loaded multi-agent: {agent_instance.name}")

                os.remove(temp_file)

            except Exception as e:
                logging.error(f"Error loading multi-agent {file.name} from Azure File Share: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Error loading multi-agents from Azure File Share: {str(e)}")

    return declared_agents

class Assistant:
    def __init__(self, declared_agents):
        self.config = {
            'assistant_name': str(os.environ.get('ASSISTANT_NAME', 'GameMaster')),
            'characteristic_description': str(os.environ.get('CHARACTERISTIC_DESCRIPTION', 'An immersive AI game master for dynamic storytelling'))
        }

        try:
            api_key = os.environ.get('AZURE_OPENAI_API_KEY')
            endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
            api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-01')
            
            if not api_key or not endpoint:
                raise ValueError("Azure OpenAI API key and endpoint are required")
            
            logging.info(f"Initializing Azure OpenAI with endpoint: {endpoint}, version: {api_version}")
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
        except Exception as e:
            logging.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise

        self.known_agents = self.reload_agents(declared_agents)
        
        self.user_guid = DEFAULT_USER_GUID
        
        self.shared_memory = None
        self.user_memory = None
        self.storage_manager = AzureFileStorageManager()
        
        self._initialize_context_memory(DEFAULT_USER_GUID)

    def _check_first_message_for_guid(self, conversation_history):
        """Check if the first message contains only a GUID"""
        if not conversation_history or len(conversation_history) == 0:
            return None
            
        first_message = conversation_history[0]
        if first_message.get('role') == 'user':
            content = first_message.get('content')
            if content is None:
                return None
            content = str(content).strip()
            guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            if guid_pattern.match(content):
                return content
        return None

    def _initialize_context_memory(self, user_guid=None):
        """Initialize context memory with separate shared and user-specific memories"""
        try:
            context_memory_agent = self.known_agents.get('ContextMemory')
            if not context_memory_agent:
                self.shared_memory = "No shared context memory available."
                self.user_memory = "No specific context memory available."
                return

            try:
                self.storage_manager.set_memory_context(None)
                shared_result = context_memory_agent.perform(full_recall=True)
                self.shared_memory = str(shared_result)[:5000] if shared_result else "No shared context memory available."
            except Exception as e:
                logging.warning(f"Error getting shared memory: {str(e)}")
                self.shared_memory = "Context memory initialization failed."
            
            if not user_guid:
                user_guid = DEFAULT_USER_GUID
            
            try:
                self.storage_manager.set_memory_context(user_guid)
                user_result = context_memory_agent.perform(user_guid=user_guid, full_recall=True)
                self.user_memory = str(user_result)[:5000] if user_result else "No specific context memory available."
            except Exception as e:
                logging.warning(f"Error getting user memory: {str(e)}")
                self.user_memory = "Context memory initialization failed."
                
        except Exception as e:
            logging.warning(f"Error initializing context memory: {str(e)}")
            self.shared_memory = "Context memory initialization failed."
            self.user_memory = "Context memory initialization failed."
    
    def extract_user_guid(self, text):
        """Try to extract a GUID from user input, but only if it's the entire message"""
        if text is None:
            return None
            
        text_str = str(text).strip()
        
        guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        match = guid_pattern.match(text_str)
        if match:
            return match.group(0)
        
        labeled_guid_pattern = re.compile(r'^guid[:=\s]+([0-9a-f-]{36})$', re.IGNORECASE)
        match = labeled_guid_pattern.match(text_str)
        if match:
            return match.group(1)
                
        return None

    def get_agent_metadata(self):
        agents_metadata = []
        for agent in self.known_agents.values():
            if hasattr(agent, 'metadata'):
                agents_metadata.append(agent.metadata)
        return agents_metadata

    def reload_agents(self, agent_objects):
        known_agents = {}
        if isinstance(agent_objects, dict):
            for agent_name, agent in agent_objects.items():
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
                else:
                    known_agents[str(agent_name)] = agent
        elif isinstance(agent_objects, list):
            for agent in agent_objects:
                if hasattr(agent, 'name'):
                    known_agents[agent.name] = agent
        else:
            logging.warning(f"Unexpected agent_objects type: {type(agent_objects)}")
        return known_agents

    def prepare_messages(self, conversation_history):
        if not isinstance(conversation_history, list):
            conversation_history = []
            
        messages = []
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Enhanced system message for game master AI
        system_message = {
            "role": "system",
            "content": f"""
<identity>
You are {str(self.config.get('assistant_name', 'GameMaster'))}, an AI Game Master for Runecraft 3D, an immersive open-world RPG experience. You orchestrate dynamic storytelling, manage NPCs, generate quests, and create emergent gameplay through intelligent agent systems.
</identity>

<game_master_role>
You are responsible for:
- Creating dynamic, branching storylines based on player actions
- Managing NPC behaviors and dialogues through specialized agents
- Generating procedural quests and world events
- Balancing game difficulty and progression
- Creating immersive narrative experiences
- Responding to player choices with meaningful consequences
- Orchestrating multiple AI agents for different game systems
</game_master_role>

<shared_memory_output>
World State and Lore:
{str(self.shared_memory)}
</shared_memory_output>

<specific_memory_output>
Player Journey and Choices:
{str(self.user_memory)}
</specific_memory_output>

<context_instructions>
- Use shared memory for world lore, faction states, and global events
- Use specific memory for player choices, relationships, and personal quest progress
- Create emergent narratives by combining both contexts
- Ensure continuity across sessions while allowing for dynamic world evolution
</context_instructions>

<agent_orchestration>
You have access to specialized agents that control different aspects of the game:
- GameWorldAgent: Manages world state, weather, time, and environmental events
- NPCDialogueAgent: Generates dynamic NPC conversations and reactions
- QuestGeneratorAgent: Creates procedural quests based on player actions and world state
- CombatNarratorAgent: Provides narrative flavor to combat encounters
- LootMasterAgent: Generates contextual and balanced loot
- StoryProgressionAgent: Manages main story arcs and critical plot points
- RandomEventAgent: Creates unexpected encounters and world events

Use these agents to create a living, breathing world that responds to player actions.
</agent_orchestration>

<narrative_guidelines>
- Create stories that adapt to player choices, not predetermined paths
- Generate NPCs with persistent personalities and memories
- Design quests that emerge from world state and player history
- Balance challenge with player skill and progression
- Create memorable moments through unexpected events
- Maintain narrative coherence while allowing player freedom
</narrative_guidelines>

<response_format>
Structure responses with game data and narrative:

1. NARRATIVE PART: Rich storytelling and descriptions
2. GAME_DATA delimiter |||GAME_DATA|||
3. JSON game state updates for the client

Example:
The ancient dragon's eyes narrow as you approach...

|||GAME_DATA|||
{{"event": "boss_encounter", "boss_id": "ancient_dragon", "dialogue": "..."}}
</response_format>
"""
        }
        messages.append(ensure_string_content(system_message))
        
        guid_only_first_message = self._check_first_message_for_guid(conversation_history)
        start_idx = 1 if guid_only_first_message else 0
        
        for i in range(start_idx, len(conversation_history)):
            messages.append(ensure_string_content(conversation_history[i]))
            
        return messages
    
    def get_openai_api_call(self, messages):
        try:
            deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-deployment')
            
            response = self.client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                functions=self.get_agent_metadata(),
                function_call="auto"
            )
            return response
        except Exception as e:
            logging.error(f"Error in OpenAI API call: {str(e)}")
            raise
    
    def parse_response_with_game_data(self, content):
        """Parse the response to extract narrative and game data parts"""
        if not content:
            return "", {}
        
        parts = content.split("|||GAME_DATA|||")
        
        if len(parts) >= 2:
            narrative_response = parts[0].strip()
            try:
                game_data = json.loads(parts[1].strip())
            except:
                game_data = {}
        else:
            narrative_response = content.strip()
            game_data = {}
        
        return narrative_response, game_data

    def get_response(self, prompt, conversation_history, max_retries=3, retry_delay=2):
        try:
            if isinstance(conversation_history, list):
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                    logging.info(f"Trimmed conversation history to last 20 messages")
            
            guid_from_history = self._check_first_message_for_guid(conversation_history)
            guid_from_prompt = self.extract_user_guid(prompt)
            
            target_guid = guid_from_history or guid_from_prompt
            
            if target_guid and target_guid != self.user_guid:
                self.user_guid = target_guid
                self._initialize_context_memory(self.user_guid)
                logging.info(f"User GUID updated to: {self.user_guid}")
            elif not self.user_guid:
                self.user_guid = DEFAULT_USER_GUID
                self._initialize_context_memory(self.user_guid)
                logging.info(f"Using default User GUID: {self.user_guid}")
            
            prompt = str(prompt) if prompt is not None else ""
            
            if guid_from_prompt and prompt.strip() == guid_from_prompt and self.user_guid == guid_from_prompt:
                formatted = "Game world initialized. Your adventure awaits!"
                game_data = {"event": "world_init", "status": "ready"}
                return formatted, json.dumps(game_data), ""
            
            messages = self.prepare_messages(conversation_history)
            messages.append(ensure_string_content({"role": "user", "content": prompt}))

            agent_logs = []
            retry_count = 0
            needs_follow_up = False

            while retry_count < max_retries:
                try:
                    response = self.get_openai_api_call(messages)
                    assistant_msg = response.choices[0].message
                    msg_contents = assistant_msg.content or ""

                    if not assistant_msg.function_call:
                        narrative_response, game_data = self.parse_response_with_game_data(msg_contents)
                        return narrative_response, json.dumps(game_data), "\n".join(map(str, agent_logs))

                    agent_name = str(assistant_msg.function_call.name)
                    agent = self.known_agents.get(agent_name)

                    if not agent:
                        return f"Agent '{agent_name}' does not exist", "{}", ""

                    json_data = ensure_string_function_args(assistant_msg.function_call)
                    logging.info(f"JSON data before parsing: {json_data}")

                    try:
                        agent_parameters = safe_json_loads(json_data)
                        
                        sanitized_parameters = {}
                        for key, value in agent_parameters.items():
                            if value is None:
                                sanitized_parameters[key] = ""
                            else:
                                sanitized_parameters[key] = value
                        
                        if agent_name in ['ManageMemory', 'ContextMemory', 'GameWorldAgent', 'NPCDialogueAgent', 
                                         'QuestGeneratorAgent', 'CombatNarratorAgent', 'LootMasterAgent',
                                         'StoryProgressionAgent', 'RandomEventAgent']:
                            sanitized_parameters['user_guid'] = self.user_guid
                        
                        result = agent.perform(**sanitized_parameters)
                        
                        if result is None:
                            result = "Agent completed successfully"
                        else:
                            result = str(result)
                            
                        agent_logs.append(f"Performed {agent_name} and got result: {result}")
                            
                    except Exception as e:
                        logging.error(f"Error in agent execution: {str(e)}")
                        return f"Error executing agent: {str(e)}", "{}", ""

                    messages.append({
                        "role": "function",
                        "name": agent_name,
                        "content": result
                    })
                    
                    try:
                        result_json = json.loads(result)
                        needs_follow_up = False
                        if isinstance(result_json, dict):
                            if result_json.get('error') or result_json.get('status') == 'incomplete':
                                needs_follow_up = True
                            if result_json.get('requires_additional_action') == True:
                                needs_follow_up = True
                    except:
                        needs_follow_up = False
                    
                    if not needs_follow_up:
                        final_response = self.get_openai_api_call(messages)
                        final_msg = final_response.choices[0].message
                        final_content = final_msg.content or ""
                        narrative_response, game_data = self.parse_response_with_game_data(final_content)
                        return narrative_response, json.dumps(game_data), "\n".join(map(str, agent_logs))

                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logging.warning(f"Error occurred: {str(e)}. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logging.error(f"Max retries reached. Error: {str(e)}")
                        return "An error occurred. Please try again.", "{}", ""

            return "Service temporarily unavailable. Please try again later.", "{}", ""
            
        except Exception as e:
            logging.error(f"Critical error in get_response: {str(e)}")
            return "A critical error occurred. Please try again.", "{}", ""

app = func.FunctionApp()

@app.route(route="businessinsightbot_function", auth_level=func.AuthLevel.FUNCTION)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    origin = req.headers.get('origin')
    cors_headers = build_cors_response(origin)

    if req.method == 'OPTIONS':
        return func.HttpResponse(
            status_code=200,
            headers=cors_headers
        )

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON in request body",
            status_code=400,
            headers=cors_headers
        )

    if not req_body:
        return func.HttpResponse(
            "Missing JSON payload in request body",
            status_code=400,
            headers=cors_headers
        )

    user_input = req_body.get('user_input')
    if user_input is None:
        user_input = ""
    else:
        user_input = str(user_input)
    
    conversation_history = req_body.get('conversation_history', [])
    if not isinstance(conversation_history, list):
        conversation_history = []
    
    user_guid = req_body.get('user_guid')
    
    is_guid_only = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', user_input.strip(), re.IGNORECASE)
    
    if not is_guid_only and not user_input.strip():
        return func.HttpResponse(
            json.dumps({
                "error": "Missing or empty user_input in JSON payload"
            }),
            status_code=400,
            mimetype="application/json",
            headers=cors_headers
        )

    try:
        agents = load_agents_from_folder()
        assistant = Assistant(agents)
        
        if user_guid:
            assistant.user_guid = user_guid
            assistant._initialize_context_memory(user_guid)
        elif is_guid_only:
            assistant.user_guid = user_input.strip()
            assistant._initialize_context_memory(user_input.strip())
            
        assistant_response, game_data, agent_logs = assistant.get_response(
            user_input, conversation_history)

        response = {
            "assistant_response": str(assistant_response),
            "game_data": game_data,
            "agent_logs": str(agent_logs),
            "user_guid": assistant.user_guid
        }

        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            headers=cors_headers
        )
    except Exception as e:
        error_response = {
            "error": "Internal server error",
            "details": str(e)
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json",
            headers=cors_headers
        )