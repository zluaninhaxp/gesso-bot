import re
from core.extractors import extract_valor, extract_dias

def classify_text(texto):

    eventos = []
    frases = re.split(r'\.\s*', texto)

    for frase in frases:
        frase = frase.strip()
        if not frase:
            continue

        frase_lower = frase.lower()

        # =============================
        # ORÇAMENTO
        # =============================
        if "orçamento" in frase_lower:

            clientes = re.findall(
                r'com\s+(?:a\s+|o\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
                frase
            )

            dias = extract_dias(frase)

            if len(clientes) == len(dias):
                for cliente, dia in zip(clientes, dias):
                    eventos.append({
                        "tipo": "orcamento_agendado",
                        "dados": {
                            "cliente": cliente,
                            "dias": [dia]
                        }
                    })
            else:
                for cliente in clientes:
                    eventos.append({
                        "tipo": "orcamento_agendado",
                        "dados": {
                            "cliente": cliente,
                            "dias": dias
                        }
                    })
            continue

        # =============================
        # RECEITA
        # =============================
        if any(p in frase_lower for p in ["recebi", "me pagou", "transferiu"]):

            nome_match = re.search(
                r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\b',
                frase
            )
            cliente = nome_match.group(1) if nome_match else ""

            eventos.append({
                "tipo": "receita",
                "dados": {
                    "cliente": cliente,
                    "valor": extract_valor(frase)
                }
            })
            continue

        # =============================
        # TAREFA
        # =============================
        if any(p in frase_lower for p in [
            "tenho que", "preciso", "ir", "terminar", "revisar"
        ]):

            cliente_match = re.search(
                r'(?:do|da|na|no|de)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
                frase
            )

            cliente = cliente_match.group(1) if cliente_match else ""

            eventos.append({
                "tipo": "tarefa",
                "dados": {
                    "cliente": cliente,
                    "descricao": frase,
                    "dias": extract_dias(frase)
                }
            })
            continue

        # =============================
        # DESPESA
        # =============================
        if any(p in frase_lower for p in ["paguei", "comprei", "gastei"]):

            eventos.append({
                "tipo": "despesa",
                "dados": {
                    "descricao": frase,
                    "valor": extract_valor(frase)
                }
            })
            continue

        # =============================
        # NÃO CLASSIFICADO
        # =============================
        eventos.append({
            "tipo": "nao_classificado",
            "dados": {
                "descricao": frase
            }
        })

    return eventos