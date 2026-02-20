import re

def extract_valor(frase):
    match = re.search(
        r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\b',
        frase
    )
    return match.group(0) if match else ""

def extract_nome(frase):
    match = re.search(
        r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\b',
        frase
    )
    return match.group(1) if match else ""

def extract_dias(frase):
    return re.findall(
        r"(segunda|terça|quarta|quinta|sexta|sábado|domingo)",
        frase.lower()
    )