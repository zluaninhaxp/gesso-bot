"""
test_classifier.py
==================
Testes do classificador financeiro — duas camadas (regex + Gemini fallback).
Execute: python test_classifier.py
"""

from core.classifier import classify_text, split_intencoes
import json

# ================================================================
# CASOS DE TESTE
# ================================================================

exemplos = [

    # ── RECEITAS ─────────────────────────────────────────────────
    {"grupo": "RECEITA", "nome": "Formal com cliente",
     "texto": "Quinta recebi 2.500 da Ana pelo serviço."},

    {"grupo": "RECEITA", "nome": "Com transferência",
     "texto": "O João me transferiu 1200 na terça."},

    {"grupo": "RECEITA", "nome": "Informal — caiu no pix",
     "texto": "Caiu no pix 800 do Carlos."},

    {"grupo": "RECEITA", "nome": "Informal — me pagaram",
     "texto": "Me pagaram 3000 hoje, tava esperando isso."},

    {"grupo": "RECEITA", "nome": "Gíria — caiu grana",
     "texto": "Caiu grana do serviço, 1500."},

    {"grupo": "RECEITA", "nome": "Informal — acertamos",
     "texto": "Acertamos com o cliente ontem, recebi 4000."},

    # ── DESPESA SERVIÇO — funcionario ────────────────────────────
    {"grupo": "DS-FUNCIONARIO", "nome": "Ajudante formal",
     "texto": "Paguei o ajudante 300 hoje."},

    {"grupo": "DS-FUNCIONARIO", "nome": "Gíria — rapaziada",
     "texto": "Paguei a rapaziada da obra, foram 600 reais."},

    {"grupo": "DS-FUNCIONARIO", "nome": "Diária com nome",
     "texto": "Paguei diária do Marcos, 200 reais."},

    {"grupo": "DS-FUNCIONARIO", "nome": "Mão de obra genérica",
     "texto": "Gastei 800 com mão de obra essa semana."},

    # ── DESPESA SERVIÇO — material ───────────────────────────────
    {"grupo": "DS-MATERIAL", "nome": "Tinta",
     "texto": "Comprei tinta por 250 reais."},

    {"grupo": "DS-MATERIAL", "nome": "Múltiplos materiais",
     "texto": "Gastei 180 com gesso e areia para a obra."},

    {"grupo": "DS-MATERIAL", "nome": "Material genérico",
     "texto": "Sexta comprei material para o serviço por 780."},

    # ── DESPESA SERVIÇO — transporte ─────────────────────────────
    {"grupo": "DS-TRANSPORTE", "nome": "Gasolina formal",
     "texto": "Coloquei gasolina por 150 reais para ir à obra."},

    {"grupo": "DS-TRANSPORTE", "nome": "Gíria — abasteci",
     "texto": "Abasteci o carro hoje, gastei 120."},

    {"grupo": "DS-TRANSPORTE", "nome": "Frete",
     "texto": "Paguei 200 de frete para entrega do material."},

    # ── DESPESA PESSOAL — alimentacao ───────────────────────────
    {"grupo": "DP-ALIMENTACAO", "nome": "Mercado simples",
     "texto": "Fui no mercado e gastei 700 reais."},

    {"grupo": "DP-ALIMENTACAO", "nome": "Mercado + comida (sem vírgula)",
     "texto": "Fui no mercado e gastei 700 reais e pedi comida por 17"},

    {"grupo": "DP-ALIMENTACAO", "nome": "Rancho do mês",
     "texto": "Fiz o rancho do mês, saiu 450."},

    {"grupo": "DP-ALIMENTACAO", "nome": "Restaurante gíria",
     "texto": "Almoçamos fora hoje, foi 85 reais."},

    # ── DESPESA PESSOAL — moradia ───────────────────────────────
    {"grupo": "DP-MORADIA", "nome": "Aluguel",
     "texto": "Paguei aluguel da casa, 1200 reais."},

    {"grupo": "DP-MORADIA", "nome": "Conta de luz",
     "texto": "Paguei conta de luz, 180 reais."},

    # ── DESPESA PESSOAL — saude ─────────────────────────────────
    {"grupo": "DP-SAUDE", "nome": "Farmácia",
     "texto": "Comprei remédio na farmácia, gastei 75."},

    {"grupo": "DP-SAUDE", "nome": "Médico",
     "texto": "Paguei a consulta do médico, 250 reais."},

    # ── SEM PONTUAÇÃO ────────────────────────────────────────────
    {"grupo": "SEM-PONTUACAO", "nome": "Dois eventos sem vírgula",
     "texto": "recebi 1500 do João comprei tinta 200"},

    {"grupo": "SEM-PONTUACAO", "nome": "Três eventos sem nada",
     "texto": "recebi 3000 do Carlos paguei ajudante 400 coloquei gasolina 100"},

    {"grupo": "SEM-PONTUACAO", "nome": "Texto corrido informal",
     "texto": "hoje caiu 2000 no pix do cliente aí fui no mercado gastei 300 e paguei a conta de luz 150"},

    # ── LINGUAGEM MUITO INFORMAL ──────────────────────────────────
    {"grupo": "INFORMAL", "nome": "Caiu no pix + mercado",
     "texto": "Caiu 1800 no pix e fui no supermercado gastei uns 200"},

    {"grupo": "INFORMAL", "nome": "Gíria múltipla",
     "texto": "Me pagaram 2500 hoje aí botei gasolina 130 e paguei a rapaziada 500"},

    {"grupo": "INFORMAL", "nome": "Expressão de gasto",
     "texto": "Desembolsei 800 com material da obra essa semana"},

    # ── CASOS MISTOS ─────────────────────────────────────────────
    {"grupo": "MISTO", "nome": "Receita + material",
     "texto": "Recebi 3000 da Ana, mas comprei tinta por 300."},

    {"grupo": "MISTO", "nome": "Três tipos diferentes",
     "texto": "Paguei o ajudante 250, comprei tinta por 180 e coloquei gasolina por 90."},

    {"grupo": "MISTO", "nome": "Semana completa",
     "texto": (
         "Segunda recebi 4000 da empresa ABC. "
         "Terça comprei material por 1200. "
         "Quarta paguei o ajudante João 300. "
         "Quinta abasteci por 120. "
         "Sexta paguei conta de luz da minha casa, 180 reais."
     )},

    # ── EDGE CASES ───────────────────────────────────────────────
    {"grupo": "EDGE", "nome": "Sem categoria (vai pro Gemini)",
     "texto": "Paguei 500 hoje."},

    {"grupo": "EDGE", "nome": "Não financeiro",
     "texto": "Preciso terminar o serviço do Carlos amanhã."},
]


# ================================================================
# RUNNER
# ================================================================

def testar(nome, texto, grupo=""):
    print(f"\n{'─' * 60}")
    print(f"[{grupo}] {nome}")
    print(f"Texto: {texto}")
    print()

    eventos = classify_text(texto)
    for i, ev in enumerate(eventos, 1):
        d = ev["dados"]
        fonte = " [gemini]" if d.get("fonte") == "gemini" else ""
        tags = ", ".join(d.get("tags", [])) or "—"
        valor = d.get("valor") or "—"
        cliente = d.get("cliente") or "—"
        aviso = f" ⚠ {d['aviso']}" if d.get("aviso") else ""
        print(f"  [{i}] {ev['tipo']}{fonte}")
        print(f"       valor={valor}  tags={tags}  cliente={cliente}{aviso}")

    return eventos


def main():
    print("\n" + "=" * 60)
    print("🧪 TESTE DO CLASSIFICADOR FINANCEIRO v4")
    print("=" * 60)

    grupos = {}
    resultados = []

    for ex in exemplos:
        grupo = ex.get("grupo", "GERAL")
        if grupo not in grupos:
            grupos[grupo] = []
            print(f"\n{'═' * 60}")
            print(f"  {grupo}")
            print(f"{'═' * 60}")

        grupos[grupo].append(ex["nome"])
        eventos = testar(ex["nome"], ex["texto"], grupo)
        tipos = [
            f"{e['tipo']}"
            + (f"({','.join(e['dados'].get('tags',[]))})" if e['dados'].get('tags') else "")
            + (" [G]" if e['dados'].get('fonte') == 'gemini' else "")
            for e in eventos
        ]
        resultados.append((ex["nome"], len(eventos), tipos))

    print("\n\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)
    for nome, n, tipos in resultados:
        print(f"  {nome}: {n} evento(s) → {', '.join(tipos)}")
    print()


if __name__ == "__main__":
    main()
