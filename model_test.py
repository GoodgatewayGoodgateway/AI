import google.generativeai as genai
genai.configure(api_key="AIzaSyBAwbjWolAj4jeG9-M72vovqdv8_LhTfl8")
print([m.name for m in genai.list_models()])