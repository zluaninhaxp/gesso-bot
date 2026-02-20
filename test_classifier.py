"""
Script de teste rápido para o classificador.
Execute: python test_classifier.py
"""

from core.classifier import classify_text
import json

# ============================================================================
# EXEMPLOS DE TESTE
# ============================================================================

exemplos = [
    {
        "nome": "Exemplo Original (Complexo)",
        "texto": (
            "Quinta eu recebi 2.500 da Ana, mas sexta tenho que revisar o orçamento da casa da Maria, "
            "e segunda marquei orçamento com a Joana e com o Carlos, mas o Carlos só confirmou para terça — "
            "e ainda comprei material por 780."
        )
    },
    {
        "nome": "Receita Simples",
        "texto": "Segunda recebi 1500 do João."
    },
    {
        "nome": "Múltiplas Receitas",
        "texto": "Terça recebi 500 da Maria, quarta recebi 800 do Pedro."
    },
    {
        "nome": "Despesa Simples",
        "texto": "Comprei tinta por 250 reais."
    },
    {
        "nome": "Despesa com Dia",
        "texto": "Sexta paguei 1200 de material."
    },
    {
        "nome": "Orçamento Simples",
        "texto": "Segunda marquei orçamento com a Ana."
    },
    {
        "nome": "Múltiplos Orçamentos",
        "texto": "Terça marquei orçamento com o Carlos e com a Joana."
    },
    {
        "nome": "Orçamento com Confirmação",
        "texto": "Segunda marquei orçamento com o Pedro, mas ele só confirmou para quarta."
    },
    {
        "nome": "Tarefa Simples",
        "texto": "Quinta tenho que ir na casa do João."
    },
    {
        "nome": "Tarefa com Orçamento",
        "texto": "Sexta preciso revisar o orçamento da casa da Maria."
    },
    {
        "nome": "Receita e Despesa",
        "texto": "Recebi 3000 da Ana, mas paguei 500 de material."
    },
    {
        "nome": "Múltiplos Eventos",
        "texto": (
            "Segunda recebi 2000 do Carlos. Terça marquei orçamento com a Maria. "
            "Quarta comprei material por 600."
        )
    },
    {
        "nome": "Valores com Vírgula",
        "texto": "Recebi 2,500 da Ana e paguei 1,200 de material."
    },
    {
        "nome": "Receita sem Cliente Explícito",
        "texto": "Quinta recebi 1500."
    },
    {
        "nome": "Orçamento e Tarefa",
        "texto": (
            "Segunda marquei orçamento com a Joana, mas terça tenho que revisar "
            "o orçamento da casa do Carlos."
        )
    },
    {
        "nome": "Confirmação Múltipla",
        "texto": (
            "Segunda marquei orçamento com a Ana e com o Pedro. "
            "A Ana confirmou para terça, mas o Pedro só confirmou para quinta."
        )
    },
    {
        "nome": "Receita com Transferência",
        "texto": "O João me transferiu 2500 na segunda."
    },
    {
        "nome": "Despesa Múltipla",
        "texto": "Comprei tinta por 300 e paguei 200 de transporte."
    },
    {
        "nome": "Tarefa Múltipla",
        "texto": "Preciso termar o serviço do Carlos e revisar o orçamento da Maria."
    },
    {
        "nome": "Frase Longa Complexa",
        "texto": (
            "Segunda recebi 5000 da empresa ABC, terça marquei orçamento com a Joana e com o Carlos, "
            "quarta tenho que revisar o orçamento da casa da Maria, quinta comprei material por 1200, "
            "mas o Carlos só confirmou para sexta."
        )
    },
    {
        "nome": "Valores Grandes",
        "texto": "Recebi 15.000 do cliente grande e paguei 3.500 de material."
    },
    {
        "nome": "Orçamento sem Dia",
        "texto": "Marquei orçamento com a Ana."
    },
    {
        "nome": "Tarefa sem Cliente",
        "texto": "Preciso comprar material amanhã."
    },
]

# ============================================================================
# EXECUTA OS TESTES
# ============================================================================

def testar_exemplo(nome, texto):
    """Testa um exemplo e imprime os resultados."""
    print(f"\n{'=' * 70}")
    print(f"TESTE: {nome}")
    print('=' * 70)
    print(f"\nTexto:\n{texto}\n")
    print("-" * 70)
    
    eventos = classify_text(texto)
    
    print(f"\n✅ Eventos encontrados: {len(eventos)}\n")
    
    if eventos:
        for i, evento in enumerate(eventos, start=1):
            print(f"📌 Evento {i} - {evento['tipo']}")
            print(json.dumps(evento['dados'], indent=2, ensure_ascii=False))
            print()
    else:
        print("⚠️  Nenhum evento encontrado!\n")
    
    return eventos


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print("🧪 TESTE DO CLASSIFICADOR - GESSOBOT")
    print("=" * 70)
    
    resultados = []
    
    for exemplo in exemplos:
        eventos = testar_exemplo(exemplo["nome"], exemplo["texto"])
        resultados.append({
            "nome": exemplo["nome"],
            "eventos": len(eventos),
            "tipos": [e["tipo"] for e in eventos]
        })
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES")
    print("=" * 70)
    print(f"\nTotal de exemplos testados: {len(exemplos)}\n")
    
    for resultado in resultados:
        tipos_str = ", ".join(resultado["tipos"]) if resultado["tipos"] else "nenhum"
        print(f"  • {resultado['nome']}: {resultado['eventos']} evento(s) - {tipos_str}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
