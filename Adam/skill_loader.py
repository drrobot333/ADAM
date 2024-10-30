import os
import utils as U
from javascript import require


def _skill_loader(skill: str):
    file_path = os.path.abspath(os.path.dirname(__file__))
    file_path = U.f_join(file_path, 'ActionLib', skill + '.js')
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content


def process_message(message):
    retry = 3
    error = None
    while retry > 0:
        try:
            babel = require("@babel/core")
            babel_generator = require("@babel/generator").default
            code = message
            parsed = babel.parse(code)
            functions = []
            assert len(list(parsed.program.body)) > 0, "No functions found"
            for i, node in enumerate(parsed.program.body):
                if node.type != "FunctionDeclaration":
                    continue
                node_type = (
                    "AsyncFunctionDeclaration"
                    if node["async"]
                    else "FunctionDeclaration"
                )
                functions.append(
                    {
                        "name": node.id.name,
                        "type": node_type,
                        "body": babel_generator(node).code,
                        "params": list(node["params"]),
                    }
                )
            # find the last async function
            main_function = None
            for function in reversed(functions):
                if function["type"] == "AsyncFunctionDeclaration":
                    main_function = function
                    break
            assert (
                    main_function is not None
            ), "No async function found. Your main function must be async."
            assert (
                    len(main_function["params"]) == 1
                    and main_function["params"][0].name == "bot"
            ), f"Main function {main_function['name']} must take a single argument named 'bot'"
            program_code = "\n\n".join(function["body"] for function in functions)
            exec_code = f"await {main_function['name']}(bot);"
            return {
                "program_code": program_code,
                "program_name": main_function["name"],
                "exec_code": exec_code,
            }
        except Exception as e:
            retry -= 1
            error = e
    return f"Error parsing action response (before program execution): {error}"


def load_control_primitives(primitive_names=None):
    file_path = os.path.abspath(os.path.dirname(__file__))
    if primitive_names is None:
        primitive_names = [
            primitives[:-3]
            for primitives in os.listdir(f"{file_path}/control_primitives")
            if primitives.endswith(".js")
        ]
    primitives = [
        U.load_text(f"{file_path}/control_primitives/{primitive_name}.js")
        for primitive_name in primitive_names
    ]
    return primitives


def skill_loader(skill: str):
    parsed_result = process_message(_skill_loader(skill))
    return "\n".join(load_control_primitives()) + "\n" + parsed_result["program_code"] + "\n" + \
           parsed_result["exec_code"]

#print(skill_loader('mineCoalOre'))
