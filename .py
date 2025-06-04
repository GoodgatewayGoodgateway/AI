import google.generativeai as genai

genai.configure(api_key="AIzaSyA1ZkSTHki91LwNyB5623ik9bbSVGU6ODE")
models = genai.list_models()

for m in models:
    print(m.name, "-", m.supported_generation_methods)