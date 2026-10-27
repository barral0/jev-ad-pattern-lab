"""Taxonomia de sete dimensões para classificar criativos de anúncios.

As dimensões, os valores e as descrições em inglês são adaptados de
https://github.com/artemnovitckii/ad-pattern-lab (MIT, ver THIRD_PARTY_NOTICES.md).
As descrições vão ao Jev em inglês, como no original; os rótulos em português
servem apenas à interface. A taxonomia classifica o que o criativo declara ou mostra,
nunca desempenho nem veracidade.
"""

DIMENSIONS = ('format', 'hook', 'angle', 'offer', 'proof', 'objection', 'cta')

DIMENSION_TITLES = {
    'format': 'Formato', 'hook': 'Gancho', 'angle': 'Ângulo', 'offer': 'Oferta',
    'proof': 'Prova', 'objection': 'Objeção', 'cta': 'Chamada para ação',
}

CATEGORIES = {
    'format': {
        'talking_head': 'Person addressing the viewer or teaching on camera, without a product demonstration or explicit customer testimonial',
        'creator_demo': 'Person visibly demonstrating a product, visible in the supplied images or factual visual notes',
        'testimonial': 'Person explicitly giving a testimonial, supported by words',
        'founder': 'Explicit founder explanation',
        'product': 'Product-only creative, visible in the supplied images or factual visual notes',
        'comparison': 'Explicit comparison of alternatives',
        'graphic': 'Text or review graphic, visible in the supplied images or factual visual notes',
        'mixed': 'Multiple formats evidenced',
        'unknown': 'Insufficient visual evidence',
    },
    'hook': {
        'curiosity': 'Specific unanswered question or information gap',
        'frustration': 'Recognizable customer problem',
        'result': 'Explicit desired-result promise',
        'contradiction': 'Challenges an expectation',
        'mistake': 'Warns about a mistake',
        'offer': 'Leads with a deal',
        'direct': 'Direct introduction without other mechanism',
        'unknown': 'Unclear',
    },
    'angle': {
        'business_growth': 'Growing a business, revenue, sales, marketing or customer acquisition',
        'education': 'Learning a skill, framework or method',
        'convenience': 'Time, ease or simpler routine',
        'price': 'Cost or value',
        'experience': 'Feel, enjoyment or aesthetic experience',
        'performance': 'What the product does',
        'trust': 'Credibility or reassurance',
        'identity': 'Self-expression or belonging',
        'unknown': 'Unclear',
    },
    'offer': {
        'free_resource': 'Explicit free guide, download, frameworks, roadmap, newsletter or other lead magnet',
        'workshop': 'Workshop, event, training session or seminar registration; use this when the main offer is attendance',
        'course': 'Course, coaching or ongoing training program',
        'discount': 'Explicit price reduction',
        'bundle': 'Multiple items sold together',
        'subscription': 'Recurring purchase',
        'trial': 'Trial or sample',
        'guarantee': 'Explicit guarantee',
        'none': 'No explicit offer',
        'unknown': 'Unclear',
    },
    'proof': {
        'demo': 'Demonstration visible in the supplied images or factual visual notes',
        'testimonial': 'Customer claim',
        'numbers': 'Quantitative claim',
        'comparison': 'Explicit comparison',
        'source': 'Named source or expert',
        'none': 'No support offered',
        'unknown': 'Unclear',
    },
    'objection': {
        'price': 'Addresses cost',
        'trust': 'Addresses credibility',
        'effort': 'Addresses effort or time',
        'effectiveness': 'Addresses whether it works',
        'suitability': 'Addresses who it suits',
        'none': 'None explicit',
        'unknown': 'Unclear',
    },
    'cta': {
        'buy': 'Shop or buy',
        'learn': 'Learn more',
        'signup': 'Sign up',
        'book': 'Book a call or visit',
        'message': 'Send a message',
        'none': 'No explicit CTA',
        'unknown': 'Unclear',
    },
}

# Rótulos em português. O mesmo valor pode existir em mais de uma dimensão com significado
# próprio; por isso a chave é (dimensão, valor).
LABELS_PT = {
    'format': {
        'talking_head': 'Pessoa falando à câmera', 'creator_demo': 'Demonstração por criador',
        'testimonial': 'Depoimento', 'founder': 'Fundador explica', 'product': 'Só o produto',
        'comparison': 'Comparação', 'graphic': 'Gráfico ou texto', 'mixed': 'Formato misto',
        'unknown': 'Indefinido',
    },
    'hook': {
        'curiosity': 'Curiosidade', 'frustration': 'Frustração', 'result': 'Resultado desejado',
        'contradiction': 'Contradição', 'mistake': 'Erro a evitar', 'offer': 'Começa pela oferta',
        'direct': 'Direto', 'unknown': 'Indefinido',
    },
    'angle': {
        'business_growth': 'Crescimento do negócio', 'education': 'Aprendizado', 'convenience': 'Praticidade',
        'price': 'Preço ou valor', 'experience': 'Experiência', 'performance': 'O que o produto faz',
        'trust': 'Confiança', 'identity': 'Identidade', 'unknown': 'Indefinido',
    },
    'offer': {
        'free_resource': 'Material gratuito', 'workshop': 'Workshop ou evento', 'course': 'Curso ou mentoria',
        'discount': 'Desconto', 'bundle': 'Pacote', 'subscription': 'Assinatura', 'trial': 'Teste ou amostra',
        'guarantee': 'Garantia', 'none': 'Sem oferta explícita', 'unknown': 'Indefinido',
    },
    'proof': {
        'demo': 'Demonstração', 'testimonial': 'Depoimento de cliente', 'numbers': 'Números',
        'comparison': 'Comparação', 'source': 'Fonte ou especialista', 'none': 'Sem prova', 'unknown': 'Indefinido',
    },
    'objection': {
        'price': 'Custo', 'trust': 'Credibilidade', 'effort': 'Esforço ou tempo', 'effectiveness': 'Funciona?',
        'suitability': 'Para quem serve', 'none': 'Nenhuma explícita', 'unknown': 'Indefinido',
    },
    'cta': {
        'buy': 'Comprar', 'learn': 'Saber mais', 'signup': 'Cadastrar-se', 'book': 'Agendar',
        'message': 'Enviar mensagem', 'none': 'Sem chamada explícita', 'unknown': 'Indefinido',
    },
}

# Hipóteses de teste, em português, adaptadas das sugestões do projeto de referência.
# São pontos de partida para um criativo original, não receitas de desempenho.
NEXT_TESTS = {
    'talking_head': 'Abra com um problema específico do negócio, ensine um passo aplicável e termine com um próximo passo relevante.',
    'free_resource': 'Ofereça um framework ou guia útil para um problema bem nomeado. Diga o que a pessoa recebe e como obter.',
    'workshop': 'Diga para quem é o evento, qual habilidade será praticada e qual é o passo real de inscrição.',
    'course': 'Explique a habilidade e o público com clareza. Use detalhes do curso que você consiga sustentar e um próximo passo claro.',
    'creator_demo': 'Mostre o produto resolvendo uma etapa chata logo no primeiro plano. Explique depois da demonstração.',
    'comparison': 'Coloque duas rotinas lado a lado. Compare uma diferença útil e facilite a escolha.',
    'testimonial': 'Comece por uma situação específica de um cliente. Use uma fala real e comprovada e mostre a rotina por trás dela.',
    'founder': 'Explique o problema que levou você a criar o produto. Mostre uma escolha que você fez de forma diferente.',
    'graphic': 'Deixe um benefício legível de relance. Mantenha o produto e o próximo passo no mesmo quadro.',
    'product': 'Mostre o produto em contexto. Responda a uma objeção em vez de listar todos os recursos.',
    'frustration': 'Abra com um problema que seu cliente já reconhece e mostre o passo que muda a situação.',
    'curiosity': 'Faça uma pergunta específica sem resposta e mostre a resposta no próprio criativo.',
    'contradiction': 'Questione uma suposição comum e demonstre a alternativa.',
    'mistake': 'Aponte um erro comum do seu cliente e mostre, na prática, como evitá-lo.',
    'result': 'Nomeie um resultado específico que você consiga sustentar e mostre o que o produto realmente faz.',
    'direct': 'Apresente o produto e o caso de uso com clareza, depois mostre-o em ação.',
    'offer': 'Diga a condição real logo no início e mantenha as regras legíveis.',
    'bundle': 'Explique por que os itens combinam. Teste a rotina como oferta, não só o desconto.',
    'discount': 'Teste a promoção contra uma versão que começa pelo problema do cliente, com o mesmo produto e público.',
    'none': 'Teste uma demonstração do produto sem gancho promocional, mantendo um próximo passo claro.',
    'trial': 'Comece por uma forma de experimentar com pouco compromisso. Diga o preço e as condições reais da amostra.',
    'subscription': 'Explique o que chega, com que frequência e como cancelar. Teste a praticidade contra uma versão focada em preço.',
    'guarantee': 'Mostre a garantia exata e suas condições. Teste, na sua própria campanha, se tratar a objeção ajuda.',
}


def title_for(dimension):
    return DIMENSION_TITLES.get(dimension, dimension)


def label_pt(dimension, value):
    """Rótulo em português; valores desconhecidos (inclusive rótulos legados) voltam como estão."""
    if value is None:
        return 'Indefinido'
    return LABELS_PT.get(dimension, {}).get(value, str(value).replace('_', ' '))
