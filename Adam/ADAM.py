import copy
import os
import re
import sys
import time
import threading
from datetime import datetime

import openai
import Adam.util_info
from concurrent.futures import ThreadPoolExecutor, as_completed
from env.bridge import VoyagerEnv
from env.process_monitor import SubprocessMonitor
from typing import Dict
from Adam.skill_loader import skill_loader
from Adam.module_utils import *
from Adam.infer_API import get_response, get_local_response
from Adam.MLLM_API import get_image_description

import wandb

lock = threading.Lock()


class ADAM:
    def __init__(
            self,
            mc_port: int = None,
            azure_login: Dict[str, str] = None,
            game_server_port: int = 3000,
            local_llm_port: int = 6000,
            local_mllm_port: int = 7000,
            game_visual_server_port: int = 9000,
            env_request_timeout: int = 180,
            env_wait_ticks: int = 10,
            max_infer_loop_num: int = 2,
            infer_sampling_num: int = 2,
            max_llm_answer_num: int = 2,
            max_try=2,
            prompt_folder_path: str = r'prompts',
            tmp_image_path: str = 'game_image',
            llm_model_type: str = 'gpt-4-turbo-preview',
            use_local_llm_service: bool = False,
            openai_api_key: str = '',
            load_ckpt_path: str = '',
            auto_load_ckpt: bool = False,
            parallel: bool = False,
            goal = []
    ):
        self.env = VoyagerEnv(
            mc_port=mc_port,
            azure_login=azure_login,
            server_port=game_server_port,
            request_timeout=env_request_timeout,
            visual_server_port=game_visual_server_port
        )
        self.default_server_port = game_server_port
        self.local_llm_port = local_llm_port
        self.local_mllm_port = local_mllm_port
        self.parallel = parallel
        if parallel:
            self.env_vector = {game_server_port: self.env}
            for i in range(1, max([infer_sampling_num, max_try])):
                self.env_vector[game_server_port + i] = VoyagerEnv(
                    mc_port=mc_port,
                    azure_login=azure_login,
                    server_port=game_server_port + i,
                    request_timeout=env_request_timeout,
                )

        self.current_time_str = datetime.now().strftime("%Y%m%d%H%M%S")
        self.env_wait_ticks = env_wait_ticks
        self.max_infer_loop_num = max_infer_loop_num
        self.infer_sampling_num = infer_sampling_num
        self.tmp_image_path = tmp_image_path
        self.dataset_path = U.f_mkdir(os.path.abspath(os.path.dirname(__file__)), "causal_datasets", llm_model_type)
        self.container_name = os.environ.get('CONTAINER_NAME')
        self.step_num = 0
        U.f_mkdir(self.dataset_path, 'causal_result')
        U.f_mkdir(self.dataset_path, 'llm_result')
        U.f_mkdir(self.dataset_path, 'mllm_result')
        U.f_mkdir(self.dataset_path, 'llm_steps_log')
        U.f_mkdir(self.dataset_path, 'log_data')
        U.f_mkdir(self.dataset_path, 'goal')
        self.ckpt_path = U.f_mkdir(self.dataset_path, 'ckpt', get_time())
        with open(prompt_folder_path + '/LLM_CD_prompt.txt', 'r') as prompt_file:
            self.CD_prompt = prompt_file.read()
        with open(prompt_folder_path + '/planner_prompt.txt', 'r') as prompt_file:
            self.planner_prompt = prompt_file.read()
        with open(prompt_folder_path + '/actor_prompt.txt', 'r') as prompt_file:
            self.actor_prompt = prompt_file.read()
        with open(U.f_join(self.dataset_path, 'goal', f'goal.txt'), 'a') as goal_file:
            goal_file.write(str(goal) + "\n\n")
        self.max_try = max_try
        self.max_llm_answer_num = max_llm_answer_num
        self.llm_model_type = llm_model_type
        self.use_local_llm_service = use_local_llm_service
        self.record = None
        self.loop_record = None
        # Observation Item Space S
        self.observation_item_space = []
        self.unlocked_actions = ['A']
        # Learned causal subgraph is represented as {action : [[causes],[effects]]}
        self.learned_causal_subgraph = {}
        self.learned_items = set()
        self.goal = ([], [])
        self.goal_item_letters = translate_item_name_list_to_letter(self.goal[0])
        self.memory = []
        if load_ckpt_path:
            self.load_state(load_ckpt_path)
        if auto_load_ckpt:
            self.auto_load_state()
        openai.api_key = openai_api_key

        wandb.init(config={
            "items":",".join(goal[0]), 
            "environment":",".join(goal[1]),
            "container":self.container_name,
            "time":self.current_time_str
            })
    def get_llm_answer(self, prompt):
        if self.use_local_llm_service:
            response_text = get_local_response(prompt, self.local_llm_port)
        else:
            response_text = get_response(prompt, self.llm_model_type)
        return response_text

    def check_llm_answer(self, prompt_text):
        for _ in range(self.max_llm_answer_num):
            try:
                response_text = self.get_llm_answer(prompt_text)
                extracted_response = re.search(r'{(.*?)}', response_text).group(1)
                cause, effect = extracted_response.strip("{}").replace(" ", "").split(";")
            except Exception as e:
                print("\033[91mLLM inference failed:" + str(e) + '\033[0m')
                continue
            if cause == '':
                cause = []
            else:
                cause = cause.split(",")
            if effect == '':
                effect = []
            else:
                effect = effect.split(",")
            if check_len_valid(cause) and check_len_valid(effect):
                self.loop_record["llm_answer_checks_num"] = _ + 1
                self.loop_record["llm_answer_success"] = True
                self.loop_record["llm_answer_record"].append([cause, effect])
                self.loop_record["llm_answer_content"] = response_text
                return True, cause, effect
        return False, None, None

    def init_record_structure(self, action_name):
        return {
            "loop_num": 0,
            "infer_sampling_num": self.infer_sampling_num,
            "successful": False,
            "action_type": action_name,
            "loop_list": [],
        }

    def update_available_knowledge(self, item_key):
        self.learned_items.update([item_key])
        if item_key in Adam.util_info.unlock.keys():
            self.unlocked_actions.extend(Adam.util_info.unlock[item_key])

    def update_material_dict(self, end_item):
        current_max_key = max(Adam.util_info.material_names_dict.keys(), key=key_cmp_func)
        for item in end_item.keys():
            item = rename_item(item)
            if item not in Adam.util_info.material_names_dict.values():
                current_max_key = generate_next_key(current_max_key)
                Adam.util_info.material_names_dict[current_max_key] = item
                Adam.util_info.material_names_rev_dict[item] = current_max_key
            item_key = Adam.util_info.material_names_rev_dict[item]
            if item_key not in self.observation_item_space:
                self.observation_item_space.append(item_key)

    def save_state(self):
        state = {
            'observation_item_space': self.observation_item_space,
            'unlocked_actions': self.unlocked_actions,
            'learned_causal_subgraph': self.learned_causal_subgraph,
            'learned_items': list(self.learned_items),
            'memory': self.memory,  # serve as log
            'goal': self.goal,
            'goal_item_letters': self.goal_item_letters,
            'material_names_dict': Adam.util_info.material_names_dict,
            'material_names_rev_dict': Adam.util_info.material_names_rev_dict
        }
        filepath = U.f_join(self.ckpt_path, get_time() + '.json')
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=4)

        self.save_wandb_state(filepath)

    def save_wandb_state(self, filepath):
        # Artifact 생성
        artifact = wandb.Artifact(name="-".join(self.goal[0]) + "_" + self.current_time_str, type="json_data")

        # JSON 파일 추가
        artifact.add_file(filepath)

        # Artifact를 W&B에 로깅
        wandb.log_artifact(artifact)

    def load_state(self, filepath):
        with open(filepath, 'r') as f:
            state = json.load(f)
        self.observation_item_space = state['observation_item_space']
        self.unlocked_actions = state['unlocked_actions']
        self.learned_causal_subgraph = state['learned_causal_subgraph']
        self.learned_items = set(state['learned_items'])
        self.goal = tuple(state['goal'])
        self.goal_item_letters = state['goal_item_letters']
        Adam.util_info.material_names_dict = state['material_names_dict']
        Adam.util_info.material_names_rev_dict = state['material_names_rev_dict']

    def auto_load_state(self):
        ckpt = U.f_listdir(self.dataset_path, 'ckpt', full_path=True, recursive=True)
        if ckpt:
            self.load_state(ckpt[-1])

    def get_causal_graph(self):
        return '\n'.join([f"Action: {key}; Cause: {value[0]}; Effect {value[1]}" for key, value in
                          self.learned_causal_subgraph.items()])

    def sample_action_once(self, env, action):
        options = {"inventory": {}, "mode": "hard"}
        for material in self.observation_item_space:
            options["inventory"] = get_inventory_number(options["inventory"], material)
        env.reset(options=options)
        time.sleep(1)
        result = env.step(skill_loader(action))
        time.sleep(1)
        start_item = result[0][1]['inventory']
        result = env.step('')
        time.sleep(1)
        end_item = result[0][1]['inventory']
        consumed_items, added_items = get_item_changes(start_item, end_item)
        if not added_items:
            return False
        with lock:
            recorder(start_item, end_item, consumed_items, added_items, action, self.dataset_path)
            self.update_material_dict(end_item)
        env.close()
        time.sleep(1)
        return True

    # Interaction module, sampling and recording
    def sampling_and_recording_action(self, action):
        if self.parallel:
            success_count = 0
            while success_count < self.infer_sampling_num:
                with ThreadPoolExecutor(max_workers=self.infer_sampling_num) as executor:
                    futures = []
                    for idx in range(self.infer_sampling_num):
                        futures.append(
                            executor.submit(self.sample_action_once, self.env_vector[self.default_server_port + idx],
                                            action))
                        time.sleep(0.5)
                    results = [future.result() for future in futures]
                success_count += results.count(True)
        else:
            for i in range(self.infer_sampling_num):
                print(f'Sampling {i + 1} started')
                while True:
                    try:
                        res = self.sample_action_once(self.env, action)
                        if res:
                            break
                    except Exception as e:
                        print(e)



    def causal_verification_once(self, env, options_orig, action, effect_item):
        try:
            print(f'Verification of action {action}, inventory: {options_orig["inventory"]}')
            env.reset(options=options_orig)
            time.sleep(1)
            result = env.step(skill_loader(action))
            time.sleep(1)
            start_item = result[0][1]['inventory']
            result = env.step('')
            time.sleep(1)
            end_item = result[0][1]['inventory']
            consumed_items, added_items = get_item_changes(start_item, end_item)
            with lock:
                recorder(start_item, end_item, consumed_items, added_items, action, self.dataset_path)
            env.close()
            time.sleep(1)
            return check_in_material(added_items, effect_item)
        except Exception as e:
            print(f"Error during causal verification: {e}")
            return False

    # Causal model module verification method
    def causal_verification(self, options_orig, action, effect_item):
        if self.parallel:
            with ThreadPoolExecutor(max_workers=self.max_try) as executor:
                futures = []
                for idx in range(self.max_try):
                    futures.append(
                        executor.submit(self.causal_verification_once, self.env_vector[self.default_server_port + idx],
                                        options_orig, action, effect_item))
                    time.sleep(0.5)
                results = [future.result() for future in as_completed(futures)]
            if any(results):
                return True
            return False
        else:
            for i in range(self.max_try):
                if self.causal_verification_once(self.env, options_orig, action, effect_item):
                    return True
        return False

    # Causal model module: LLM-based CD and Intervention-based CD
    def causal_learning(self, action):
        record_json_path = U.f_join(self.dataset_path, 'log_data', action + '.json')
        for loop_index in range(self.max_infer_loop_num):
            self.record["loop_num"] += 1
            self.loop_record = {"loop_id": loop_index + 1,
                                "llm_answer_record": [],
                                "llm_answer_checks_num": self.max_llm_answer_num,
                                "llm_answer_success": False,
                                "llm_answer_verification_success": False,
                                }

            print(f'Start action {action}')
            self.sampling_and_recording_action(action)

            with open(record_json_path, 'r') as file:
                data = json.load(file)
            CD_prompt = copy.deepcopy(self.CD_prompt)
            dict_string = '\n'.join(
                [f"'{key}': '{Adam.util_info.material_names_dict[key]}'" for key in self.observation_item_space])
            CD_prompt = CD_prompt.replace("{mapping}", dict_string, 1)
            for i, item in enumerate(data[(-self.infer_sampling_num):], start=1):
                initial_items = ', '.join(item['Start item'])
                consumed_items = ', '.join(item['Consumed items'])
                added_items = ', '.join(item['Added items'])
                sampling_result = f"{i}. Initial items: {initial_items}; Consumed items: {consumed_items}; Added items: {added_items}\n"
                CD_prompt += sampling_result
            CD_prompt += "\nYour inference:\n"

            flag, cause, effect = self.check_llm_answer(CD_prompt)
            if not flag:
                self.record["loop_list"].append(self.loop_record)
                print('LLM inference failed')
                continue
            print(f'Causal assumption: Cause:{cause}, Effect:{effect}')
            self.loop_record["cause_llm"] = cause
            self.loop_record['effect_llm'] = effect
            for effect_item in effect:
                options_orig = {"inventory": {}, "mode": "hard"}
                for item in cause:
                    options_orig["inventory"] = get_inventory_number(options_orig["inventory"], item)
                try:
                    if not self.causal_verification(options_orig, action, effect_item):
                        self.record["loop_list"].append(self.loop_record)
                        break
                except Exception as e:
                    print("Error: ", str(e))
                    break
                self.loop_record["llm_answer_verification_success"] = True

                # Implement do() operation for each variable in cause
                items_to_remove = []
                for item in cause:
                    options_modified = copy.deepcopy(options_orig)
                    item_name = rename_item_rev(translate_item_letter_to_name(item))
                    del options_modified["inventory"][item_name]
                    if self.causal_verification(options_modified, action, effect_item):
                        options_orig = options_modified
                        items_to_remove.append(item)

                self.loop_record['items_to_remove'] = items_to_remove
                self.loop_record['items_to_remove_length'] = len(items_to_remove)
                for item in items_to_remove:
                    cause.remove(item)

                print('Causal relation found!')
                print('Cause:', cause)
                print('Effect:', effect_item)
                self.loop_record["cause_found"] = cause
                self.loop_record["effect_found"] = effect_item
                with open(U.f_join(self.dataset_path, 'causal_result', action + '.json'), 'w') as json_file:
                    json.dump([cause, effect_item], json_file)
                self.record["successful"] = True
                self.record["loop_list"].append(self.loop_record)
                llm_steps_path = U.f_join(self.dataset_path, 'llm_steps_log', action + '.json')
                try:
                    with open(llm_steps_path, 'r') as file:
                        try:
                            logs = json.load(file)
                        except json.JSONDecodeError:
                            logs = []
                except FileNotFoundError:
                    logs = []
                logs.append(self.record)
                with open(llm_steps_path, 'w') as file:
                    json.dump(logs, file, indent=4)
                action_key = translate_action_name_to_letter(action)
                if action_key not in self.learned_causal_subgraph:
                    self.learned_causal_subgraph[action_key] = [cause, [effect_item]]
                else:
                    self.learned_causal_subgraph[action_key][1].append(effect_item)
                self.update_available_knowledge(effect_item)
                self.save_state()
            return True
        return False

    def planner(self, current_inventory):
        inventory_name_and_num = copy.deepcopy(current_inventory)
        current_inventory = translate_item_name_list_to_letter(current_inventory)
        not_obtained_items = [item for item in self.goal_item_letters if item not in current_inventory]
        planner_prompt = copy.deepcopy(self.planner_prompt)
        replacements = {
            "{goal}": ', '.join(translate_item_name_list_to_letter(self.goal[0])),
            "{mapping}": str(Adam.util_info.material_names_dict),
            "{current inventory}": ', '.join(current_inventory),
            "{inventory name and num}": str(inventory_name_and_num),
            "{lacked inventory}": ', '.join(not_obtained_items),
            "{causal graph}": self.get_causal_graph(),
        }
        for key, value in replacements.items():
            planner_prompt = planner_prompt.replace(key, value, 1)
        subtask = self.get_llm_answer(planner_prompt)
        print('\033[94m' + '-' * 20 + 'Planner' + '-' * 20 + '\n' + subtask + '\033[0m')
        return subtask

    def actor(self, subtask, perception):
        max_attempts = 3
        attempts = 0
        while attempts < max_attempts:
            try:
                actor_prompt = copy.deepcopy(self.actor_prompt)
                replacements = {
                    "{causal graph}": self.get_causal_graph(),
                    "{available actions}": ', '.join(self.unlocked_actions),
                    "{goal items}": ', '.join(translate_item_name_list_to_letter(self.goal[0])),
                    "{environmental factors}": ', '.join(self.goal[1]),
                    "{memory}": self.get_memory(),
                    "{subtasks}": subtask,
                    "{perception}": perception,
                }
                for key, value in replacements.items():
                    actor_prompt = actor_prompt.replace(key, value, 1)
                action_response = self.get_llm_answer(actor_prompt)
                print('\033[32m' + '-' * 20 + 'Actor' + '-' * 20 + '\n' + action_response + '\033[0m')
                action = translate_action_letter_to_name(re.search(r'{(.*?)}', action_response).group(1))
                break
            except Exception as e:
                attempts += 1
                print(f"Attempt {attempts}: An error occurred - {e}")
                if attempts == max_attempts:
                    return 'moveForward'
        return action

    def update_memory(self, action_letter, consumed_items, added_items, environment_description):
        self.memory.append([action_letter, consumed_items, added_items, environment_description])

    def get_memory(self):
        recent_memory = self.memory[-3:]
        formatted_prompt = []

        for entry in recent_memory:
            action_letter, consumed_items, added_items, environment_description = entry
            formatted_entry = f"Action: {action_letter}\n" \
                              f"Consumed Items: {', '.join(translate_item_name_list_to_letter(consumed_items))}\n" \
                              f"Added Items: {', '.join(translate_item_name_list_to_letter(added_items))}\n" \
                              f"Environment: {environment_description}\n" \
                              "----"
            formatted_prompt.append(formatted_entry)

        return f"The most recent {len(recent_memory)} records\n----\n" + "\n".join(formatted_prompt)

    def controller(self):
        # initial Minecraft instance
        options = {"mode": "hard"}
        self.env.reset(options=options)
        result = self.env.step('')
        self.run_visual_API()
        while True:
            try:
                environment_description = get_image_description(local_mllm_port=self.local_mllm_port)
                with open(U.f_join(self.dataset_path, 'mllm_result', f'talk_{",".join(self.goal[0])}_{self.current_time_str}.txt'), 'a') as talk_result_file:
                    talk_result_file.write(str(environment_description) + "\n\n")

                if all(item in translate_item_name_list_to_letter(result[0][1]['inventory'].keys()) for item in
                    self.goal_item_letters):
                    print(self.step_num)
                    wandb.log({"step_num":self.step_num})
                    subtask = 'Achieve the environmental factors.'
                    break
                else:
                    subtask = self.planner(result[0][1]['inventory'])
                with open(U.f_join(self.dataset_path, 'llm_result', f'talk_{",".join(self.goal[0])}_{self.current_time_str}.txt'), 'a') as talk_result_file:
                    talk_result_file.write(str(subtask) + "\n\n")
                action = self.actor(subtask, environment_description)
                self.step_num += 1
                print('Action:', action)
                result = self.env.step(skill_loader(action))
                start_item = result[0][1]['inventory']
                result = self.env.step('')
                end_item = result[0][1]['inventory']
                print('Inventory now:', str(result[0][1]['inventory']))
                print('Voxels around:', str(result[0][1]['voxels']))
                consumed_items, added_items = get_item_changes(start_item, end_item)
                recorder(start_item, end_item, consumed_items, added_items, action, self.dataset_path)
                self.update_material_dict(end_item)
                self.update_memory(action, consumed_items, added_items, environment_description)
                if self.check_goal_completed(result):
                    return
            except Exception as e:
                print(e)

    def check_goal_completed(self, result):
        return all(item in translate_item_name_list_to_letter(result[0][1]['inventory'].keys()) for item in
                   self.goal_item_letters) and all(item in result[0][1]['voxels'] for item in self.goal[1])

    def learn_new_actions(self):
        for action in reversed(self.unlocked_actions):
            if action not in self.learned_causal_subgraph.keys():
                self.record = self.init_record_structure(action)
                self.causal_learning(translate_action_letter_to_name(action))
                break

    def explore(self, goal_item, goal_environment):
        self.goal = (goal_item, goal_environment)
        self.goal_item_letters = translate_item_name_list_to_letter(self.goal[0])
        while True:
            if all(item in self.learned_items for item in self.goal_item_letters):
                break
            self.learn_new_actions()

        self.controller()
        while len(self.learned_causal_subgraph.keys()) < len(self.unlocked_actions):
            self.learn_new_actions()

    def run_visual_API(self):
        # python_executable = sys.executable
        # script_path = os.path.join(os.getcwd(), 'Adam', "visual_API.py")
        
        # commands = [python_executable, script_path]  # xvfb-run 추가

        # monitor = SubprocessMonitor(
        #     commands=commands,
        #     name="VisualAPIMonitor",
        #     ready_match=r"Visual API Ready",
        #     log_path="logs",
        #     callback_match=r"Error",
        #     callback=lambda: print("Error detected in subprocess!"),
        #     finished_callback=lambda: print("Subprocess has finished.")
        # )
        # monitor.run()

        pass

