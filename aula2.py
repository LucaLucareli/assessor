import google.generativeai as gemini
from dotenv import load_dotenv
import os

load_dotenv()
gemini.configure(api_key=os.getenv("GEMINI_API_KEY"))

llm = gemini.GenerativeModel(
    model_name = 'models/gemini-2.5-flash',
    system_instruction="Isso é um problema de lógica, que a reposta pode não ser retirada hierarquica. Considere outros exmplos: ANA é mãe, ANNA é minha irmã",
    generation_config=gemini.types.GenerationConfig(
        temperature = 0.7,
        top_p = 0.95,
        # max_output_tokens = 300
        # stop_sequences = ['\n\n\']
    )
)

user_prompt = '''
Se ARI é meu pai e BRUNO é meu primo, então CAROLINA é a minha:
a) Mãe
b) Prima
c) Tia
d) Sobrinha
e) Irmã
'''

try:
    response = llm.generate_content(user_prompt)
    print(response.text)
except Exception as e:
    print("Erro: ", e)
