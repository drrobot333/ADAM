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
    url = 'http://127.0.0.1:' + str(local_llm_port) + '/send'
    data = {'text': prompt}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        response_data = response.json()
        print(response_data.get('response', '').strip())
        return response_data.get('response', '').strip()
    else:
        return f'Error: {response.status_code}'
