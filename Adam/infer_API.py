import openai
import requests


def get_response(prompt='', model_name='gpt-4-turbo-preview'):
    response = openai.chat.completions.create(
        model=model_name,
        messages=[
            {'role': 'user', 'content': prompt
             }
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def get_local_response(prompt='', local_llm_port=6000):
    url = 'http://ksh_llm_server:' + str(local_llm_port) + '/send'
    data = {'text': prompt, 'max_tokens': 1024}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        response_data = response.json()
        print(response_data.get('response', '').strip())
        return response_data.get('response', '').strip()
    else:
        return f'Error: {response.status_code}'


# from transformers import AutoModelForCausalLM, AutoTokenizer

# # 모델과 토크나이저를 전역으로 미리 로드
# model_name = "/workspace/hdd/Qwen2.5-72B-Instruct-AWQ"
# model = AutoModelForCausalLM.from_pretrained(
#     model_name,
#     torch_dtype="auto",
#     device_map="auto"
# )
# tokenizer = AutoTokenizer.from_pretrained(model_name)

# def get_local_response(prompt='', local_llm_port=6000):
#     messages = [
#         {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
#         {"role": "user", "content": prompt}
#     ]
#     text = tokenizer.apply_chat_template(
#         messages,
#         tokenize=False,
#         add_generation_prompt=True
#     )
#     model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
#     generated_ids = model.generate(
#         **model_inputs,
#         max_new_tokens=512
#     )
#     # 입력 토큰 이후의 생성된 토큰만 추출
#     generated_ids = [
#         output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
#     ]
#     response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
#     return response.strip()
