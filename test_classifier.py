"""
Testes do classificador financeiro com sistema de tags.
Execute: python test_classifier.py
"""

from core.classifier import classify_text
import json

exemplos = [
    # ---- RECEITAS ----
    {"nome": "Receita simples com cliente",
     "texto": "Quinta recebi 2.500 da Ana."},
    {"nome": "Receita pelo serviço",
     "texto": "Segunda recebi 5000 do Carlos pelo serviço."},
    {"nome": "Receita via transferência",
     "texto": "O João me transferiu 1200 na terça."},
    {"nome": "Receita sem cliente",
     "texto": "Recebi 3000 hoje."},

    # ---- DESPESA DE SERVIÇO: funcionario ----
    {"nome": "DS – funcionario (ajudante)",
     "texto": "Paguei o ajudante 300 hoje."},
    {"nome": "DS – funcionario (diária com nome)",
     "texto": "Paguei diária do Marcos, 200 reais."},
    {"nome": "DS – funcionario (mão de obra)",
     "texto": "Gastei 800 com mão de obra nessa semana."},

    # ---- DESPESA DE SERVIÇO: material ----
    {"nome": "DS – material (tinta)",
     "texto": "Comprei tinta por 250 reais."},
    {"nome": "DS – material (gesso + areia)",
     "texto": "Gastei 180 com gesso e areia."},
    {"nome": "DS – material (genérico)",
     "texto": "Sexta comprei material por 780."},

    # ---- DESPESA DE SERVIÇO: ferramenta ----
    {"nome": "DS – ferramenta",
     "texto": "Aluguei uma betoneira por 150 para a obra."},
    {"nome": "DS – ferramenta (equipamento)",
     "texto": "Comprei equipamentos para o serviço, gastei 600."},

    # ---- DESPESA DE SERVIÇO: transporte ----
    {"nome": "DS – transporte (gasolina)",
     "texto": "Coloquei gasolina por 150 reais para ir à obra."},
    {"nome": "DS – transporte (frete)",
     "texto": "Paguei 200 de frete para entrega do material."},
    {"nome": "DS – transporte (pedágio)",
     "texto": "Gastei 45 em pedágio essa semana."},

    # ---- DESPESA DE SERVIÇO: imposto ----
    {"nome": "DS – imposto",
     "texto": "Paguei o DAS do Simples Nacional, 380 reais."},

    # ---- DESPESA PESSOAL: alimentacao ----
    {"nome": "DP – alimentacao (mercado)",
     "texto": "Fui no supermercado e gastei 350."},
    {"nome": "DP – alimentacao (restaurante)",
     "texto": "Gastei 90 no restaurante ontem."},
    {"nome": "DP – alimentacao (delivery)",
     "texto": "Pedi delivery, custou 65."},

    # ---- DESPESA PESSOAL: moradia ----
    {"nome": "DP – moradia (aluguel)",
     "texto": "Paguei aluguel da casa, 1200 reais."},
    {"nome": "DP – moradia (conta de luz)",
     "texto": "Paguei conta de luz, 180 reais."},

    # ---- DESPESA PESSOAL: saude ----
    {"nome": "DP – saude (farmácia)",
     "texto": "Comprei remédio na farmácia, gastei 75."},
    {"nome": "DP – saude (médico)",
     "texto": "Paguei a consulta do médico, 250 reais."},

    # ---- DESPESA PESSOAL: lazer ----
    {"nome": "DP – lazer",
     "texto": "Paguei a academia esse mês, 120 reais."},

    # ---- DESPESA PESSOAL: internet ----
    {"nome": "DP – internet/telefone",
     "texto": "Paguei o plano do celular, 55 reais."},

    # ---- CASOS MISTOS ----
    {"nome": "Receita + Despesa Serviço",
     "texto": "Recebi 3000 da Ana, mas comprei tinta por 300."},
    {"nome": "Múltiplos gastos de serviço",
     "texto": "Paguei o ajudante 250, comprei tinta por 180 e coloquei gasolina por 90."},
    {"nome": "Semana completa",
     "texto": (
         "Segunda recebi 4000 da empresa ABC pelo serviço. "
         "Terça comprei material por 1200. "
         "Quarta paguei o ajudante João 300. "
         "Quinta coloquei gasolina por 120. "
         "Sexta paguei conta de luz da minha casa, 180 reais."
     )},

    # ---- EDGE CASES ----
    {"nome": "Despesa sem categoria clara",
     "texto": "Paguei 500 hoje."},
    {"nome": "Frase não financeira",
     "texto": "Preciso terminar o serviço do Carlos amanhã."},
]


def testar_exemplo(nome, texto):
    print(f"\n{'=' * 65}")
    print(f"TESTE: {nome}")
    print('=' * 65)
    print(f"Texto: {texto}\n")

    eventos = classify_text(texto)
    print(f"✅ {len(eventos)} evento(s)\n")

    for i, evento in enumerate(eventos, 1):
        print(f"  📌 [{i}] {evento['tipo']}")
        print(f"  {json.dumps(evento['dados'], ensure_ascii=False, indent=4)}")
        print()

    return eventos


def main():
    print("\n" + "=" * 65)
    print("🧪 TESTE DO CLASSIFICADOR FINANCEIRO (com tags)")
    print("=" * 65)

    resultados = []
    for ex in exemplos:
        eventos = testar_exemplo(ex["nome"], ex["texto"])
        resultados.append({
            "nome": ex["nome"],
            "n": len(eventos),
            "tipos": [f"{e['tipo']}({','.join(e['dados'].get('tags', []))})" for e in eventos]
        })

    print("\n" + "=" * 65)
    print("📊 RESUMO")
    print("=" * 65)
    for r in resultados:
        print(f"  • {r['nome']}: {r['n']} evento(s) → {', '.join(r['tipos'])}")
    print()


if __name__ == "__main__":
    main()
