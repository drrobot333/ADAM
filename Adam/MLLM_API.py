import requests


def get_image_description(image_path='Adam/Adam/game_image/tmp.png', local_mllm_port=7000):
    text = 'Please describe this Minecraft image'
    url = 'http://host.docker.internal:' + str(local_mllm_port) + '/send_image_text'
    files = {'image': open(image_path, 'rb')}
    data = {'text': text}

    response = requests.post(url, data=data, files=files)


    return response.text
