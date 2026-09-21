"""Exercícios extras de gramática, por idioma e faixa.

O banco original tinha um único item por faixa. Uma resposta certa encerrava a
etapa e o cronograma abria o card de compreensão. Aqui cada faixa ganha mais
três itens, alinhados ao mesmo foco de `GRAMMAR_FOCUS`, para a prática durar
a etapa inteira em todos os idiomas.

LIMITAÇÃO: material de desenvolvimento, sem revisão de falante nativo.
"""

from __future__ import annotations

BAND_BEGINNER = "beginner"
BAND_ELEMENTARY = "elementary"
BAND_INTERMEDIATE = "intermediate"
BAND_UPPER = "upper"


def _q(prompt: str, answer: str, options: list[tuple[str, str]], rationale: str) -> dict:
    return {
        "prompt": prompt,
        "options": [text for text, _why in options],
        "answer": answer,
        "rationale": rationale,
        "option_rationales": {text: why for text, why in options},
    }


EXTRA: dict[str, dict[str, list[dict]]] = {
    "en": {
        BAND_BEGINNER: [
            _q(
                "Where ____ you from?",
                "are",
                [
                    ("are", "'Are' concorda com 'you' na pergunta de origem."),
                    ("is", "'Is' combina com he/she/it, não com 'you'."),
                    ("do", "'Do' pede um verbo de ação, não 'from'."),
                ],
                "Pergunta de origem: Where + are + you + from.",
            ),
            _q(
                "____ do you do?",
                "What",
                [
                    ("What", "'What do you do?' pergunta a ocupação."),
                    ("Where", "'Where' pergunta lugar, não ocupação."),
                    ("Who", "'Who' pergunta a pessoa, não a atividade."),
                ],
                "Pergunta de rotina/ocupação usa 'What'.",
            ),
            _q(
                "I ____ a student.",
                "am",
                [
                    ("am", "'I' pede 'am' no presente de be."),
                    ("is", "'Is' combina com he/she/it."),
                    ("are", "'Are' combina com you/we/they."),
                ],
                "Identidade no presente: I am.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "She ____ home last night.",
                "went",
                [
                    ("went", "'Last night' fecha o tempo: passado simples."),
                    ("goes", "Presente não combina com 'last night'."),
                    ("is going", "Presente contínuo descreve agora, não ontem."),
                ],
                "Marcador fechado exige passado simples.",
            ),
            _q(
                "We usually ____ coffee in the morning.",
                "drink",
                [
                    ("drink", "'Usually' marca hábito: presente simples."),
                    ("drank", "Passado não combina com um hábito atual."),
                    ("are drinking", "Contínuo descreve o momento, não a rotina."),
                ],
                "Hábito que continua válido fica no presente.",
            ),
            _q(
                "He called, then he ____.",
                "left",
                [
                    ("left", "Sequência de fatos no passado: os dois verbos no passado."),
                    ("leaves", "Presente quebra a sequência já aberta no passado."),
                    ("is leaving", "Contínuo não fecha o segundo fato da sequência."),
                ],
                "Sequência de fatos: passado em todos os verbos.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "I ____ that film.",
                "have seen",
                [
                    ("have seen", "Sem data fechada, o que importa é a experiência."),
                    ("saw", "Passado simples pede um momento específico."),
                    ("was seeing", "Contínuo descreve ação em progresso, não experiência."),
                ],
                "Experiência acumulada, sem marcador fechado.",
            ),
            _q(
                "I ____ there in 2019.",
                "went",
                [
                    ("went", "'In 2019' fecha o tempo: passado simples."),
                    ("have gone", "Present perfect não combina com ano fechado."),
                    ("have been going", "Contínuo de experiência não marca um ano fechado."),
                ],
                "Marcador fechado pede passado simples.",
            ),
            _q(
                "She ____ here since May.",
                "has worked",
                [
                    ("has worked", "'Since' marca início no passado e ação ainda válida."),
                    ("worked", "Passado simples encerraria o período."),
                    ("works", "Presente simples não carrega o 'since'."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "This ____ explain the delay.",
                "might",
                [
                    ("might", "'Might' marca possibilidade, não certeza."),
                    ("must to", "'Must' não leva 'to' antes do verbo."),
                    ("can to", "'Can' também não leva 'to'."),
                ],
                "Modal de possibilidade, sem 'to'.",
            ),
            _q(
                "If I ____ more time, I would have finished.",
                "had had",
                [
                    ("had had", "Contrafactual do passado: if + past perfect."),
                    ("have", "Presente não forma a hipótese sobre o passado."),
                    ("would have", "'Would have' fica no resultado, não no if."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "It is ____ the safer choice.",
                "arguably",
                [
                    ("arguably", "Ressalva: a escolha é defensável, não absoluta."),
                    ("argument", "Substantivo; a frase pede advérbio."),
                    ("argue", "Verbo; aqui cabe o advérbio de ressalva."),
                ],
                "Ressalva que preserva o argumento sem torná-lo categórico.",
            ),
        ],
    },
    "es-ES": {
        BAND_BEGINNER: [
            _q(
                "¿De ____ eres?",
                "dónde",
                [
                    ("dónde", "'¿De dónde eres?' pergunta a origem."),
                    ("qué", "'Qué' não forma a pergunta de origem."),
                    ("quién", "'Quién' pergunta a pessoa, não o lugar."),
                ],
                "Pergunta de origem no espanhol peninsular.",
            ),
            _q(
                "¿A qué te ____?",
                "dedicas",
                [
                    ("dedicas", "'¿A qué te dedicas?' pergunta a ocupação, com 'tú'."),
                    ("dedica", "Terceira pessoa, não a pergunta direta a 'tú'."),
                    ("dedico", "Primeira pessoa: seria a resposta, não a pergunta."),
                ],
                "Pergunta de rotina dirigida a 'tú'.",
            ),
            _q(
                "____ soy Ana.",
                "Yo",
                [
                    ("Yo", "Pronome de identidade na apresentação."),
                    ("Tú", "'Tú' seria a outra pessoa."),
                    ("Él", "'Él' não apresenta quem fala."),
                ],
                "Apresentação: quem fala é 'yo'.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "Anoche ____ a casa tarde.",
                "volví",
                [
                    ("volví", "'Anoche' fecha o tempo: pretérito indefinido."),
                    ("vuelvo", "Presente não combina com 'anoche'."),
                    ("estoy volviendo", "Progressivo descreve agora, não ontem."),
                ],
                "Marcador fechado pede indefinido.",
            ),
            _q(
                "Normalmente ____ desde casa.",
                "trabajo",
                [
                    ("trabajo", "'Normalmente' marca hábito atual."),
                    ("trabajé", "Indefinido encerraria o hábito."),
                    ("trabajaba", "Imperfecto descreve hábito passado, não o de agora."),
                ],
                "Hábito que continua válido fica no presente.",
            ),
            _q(
                "Llamó y luego ____.",
                "se fue",
                [
                    ("se fue", "Sequência no passado: os dois verbos no indefinido."),
                    ("se va", "Presente quebra a sequência."),
                    ("se iba", "Imperfecto não fecha o segundo fato pontual."),
                ],
                "Sequência de fatos pontuais no passado.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "____ esa película.",
                "He visto",
                [
                    ("He visto", "Sem data fechada: pretérito perfecto (uso peninsular)."),
                    ("Vi", "Indefinido pede um momento fechado."),
                    ("Veía", "Imperfecto descreve hábito ou fundo, não a experiência."),
                ],
                "Experiência acumulada até agora.",
            ),
            _q(
                "____ allí en 2019.",
                "Fui",
                [
                    ("Fui", "'En 2019' fecha o tempo: indefinido."),
                    ("He ido", "Perfecto não combina com ano fechado no uso peninsular."),
                    ("Iba", "Imperfecto não marca um ano pontual."),
                ],
                "Marcador fechado pede indefinido.",
            ),
            _q(
                "____ aquí desde mayo.",
                "Trabajo",
                [
                    ("Trabajo", "'Desde' + presente: a ação continua."),
                    ("Trabajé", "Indefinido encerraria o período."),
                    ("Trabajaba", "Imperfecto não marca o que ainda vale."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "Esto ____ explicar el retraso.",
                "podría",
                [
                    ("podría", "Condicional de possibilidade, não de certeza."),
                    ("debe de que", "Construção inválida para este modal."),
                    ("puede que de", "'Puede que' pede subjuntivo, não 'de' + infinitivo."),
                ],
                "Modalização: possibilidade, não afirmação categórica.",
            ),
            _q(
                "Si ____ más tiempo, lo habría terminado.",
                "hubiera tenido",
                [
                    ("hubiera tenido", "Contrafactual do passado: pluscuamperfecto de subjuntivo."),
                    ("tengo", "Presente não forma a hipótese sobre o passado."),
                    ("tuve", "Indefinido não entra nessa condicional irreal."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "Es, ____, la opción más segura.",
                "sin duda",
                [
                    ("sin duda", "Ressalva/ênfase que não transforma a frase em fato bruto."),
                    ("duda", "Substantivo solto não cabe neste encaixe."),
                    ("dudar", "Infinitivo não funciona como ressalva."),
                ],
                "Ressalva que sustenta o argumento.",
            ),
        ],
    },
    "fr": {
        BAND_BEGINNER: [
            _q(
                "D'____ venez-vous ?",
                "où",
                [
                    ("où", "'D'où venez-vous ?' pergunta a origem."),
                    ("qui", "'Qui' pergunta a pessoa."),
                    ("que", "'Que' não forma esta pergunta de lugar."),
                ],
                "Pergunta de origem.",
            ),
            _q(
                "____ faites-vous ?",
                "Que",
                [
                    ("Que", "'Que faites-vous ?' pergunta a ocupação."),
                    ("Où", "'Où' pergunta lugar."),
                    ("Qui", "'Qui' pergunta a pessoa."),
                ],
                "Pergunta de rotina.",
            ),
            _q(
                "Je ____ étudiant.",
                "suis",
                [
                    ("suis", "'Je' pede 'suis'."),
                    ("es", "'Es' é espanhol, não a forma de 'je'."),
                    ("est", "'Est' combina com il/elle."),
                ],
                "Identidade: je suis.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "Hier soir, elle ____ tard.",
                "est rentrée",
                [
                    ("est rentrée", "'Hier soir' fecha o tempo: passé composé."),
                    ("rentre", "Présent não combina com 'hier soir'."),
                    ("rentrera", "Futur aponta para depois, não para ontem."),
                ],
                "Marcador fechado pede passé composé.",
            ),
            _q(
                "D'habitude, nous ____ à la maison.",
                "travaillons",
                [
                    ("travaillons", "'D'habitude' marca hábito atual."),
                    ("avons travaillé", "Passé composé encerraria o hábito."),
                    ("travaillions", "Imparfait descreve hábito passado."),
                ],
                "Hábito que continua válido fica no presente.",
            ),
            _q(
                "Il a appelé, puis il ____.",
                "est parti",
                [
                    ("est parti", "Sequência no passado: os dois verbos no passé composé."),
                    ("part", "Présent quebra a sequência."),
                    ("partira", "Futur não fecha o segundo fato."),
                ],
                "Sequência de fatos no passado.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "J'____ ce film.",
                "ai vu",
                [
                    ("ai vu", "Sem data fechada: experiência com passé composé."),
                    ("vois", "Présent não marca a experiência acumulada."),
                    ("verrai", "Futur não descreve o que já aconteceu."),
                ],
                "Experiência, sem momento fechado.",
            ),
            _q(
                "J'y ____ en 2019.",
                "suis allé",
                [
                    ("suis allé", "'En 2019' fecha o tempo."),
                    ("vais", "Présent não combina com o ano fechado."),
                    ("irai", "Futur aponta para depois de 2019."),
                ],
                "Marcador fechado pede passé composé.",
            ),
            _q(
                "Elle travaille ici ____ mai.",
                "depuis",
                [
                    ("depuis", "'Depuis' + presente: a ação continua."),
                    ("pendant", "'Pendant' mede uma duração já encerrada."),
                    ("dans", "'Dans' aponta para o futuro ('daqui a')."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "Cela ____ expliquer le retard.",
                "pourrait",
                [
                    ("pourrait", "Conditionnel de possibilidade."),
                    ("doit de", "Construção inválida."),
                    ("peut à", "'Peut' não leva 'à' aqui."),
                ],
                "Modalização de possibilidade.",
            ),
            _q(
                "Si j'____ plus de temps, j'aurais fini.",
                "avais eu",
                [
                    ("avais eu", "Contrafactual do passado: si + plus-que-parfait."),
                    ("ai", "Présent não forma essa hipótese."),
                    ("aurais", "'Aurais' fica no resultado, não depois de si."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "C'est ____ le choix le plus sûr.",
                "sans doute",
                [
                    ("sans doute", "Ressalva: provável, não absoluto."),
                    ("doute", "Substantivo solto não cabe."),
                    ("douter", "Infinitivo não funciona como ressalva."),
                ],
                "Ressalva que preserva o argumento.",
            ),
        ],
    },
    "ja": {
        BAND_BEGINNER: [
            _q(
                "どこ____来ましたか。",
                "から",
                [
                    ("から", "「どこから」pergunta a origem."),
                    ("に", "「に」marca destino, não origem nesta pergunta."),
                    ("を", "「を」marca objeto, não origem."),
                ],
                "Pergunta de origem: どこから.",
            ),
            _q(
                "お仕事（しごと）は____ですか。",
                "何（なん）",
                [
                    ("何（なん）", "「何」pergunta a ocupação."),
                    ("どこ", "「どこ」pergunta lugar."),
                    ("だれ", "「だれ」pergunta a pessoa."),
                ],
                "Pergunta de rotina/ocupação.",
            ),
            _q(
                "わたしは学生（がくせい）____。",
                "です",
                [
                    ("です", "「です」fecha a frase de identidade no estilo polido."),
                    ("ます", "「ます」flexiona verbo de ação, não o substantivo."),
                    ("だ", "「だ」é casual; o padrão desta etapa é です."),
                ],
                "Identidade no estilo です/ます.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "昨夜（ゆうべ）家（いえ）に____。",
                "帰（かえ）りました",
                [
                    ("帰（かえ）りました", "「昨夜」fecha o tempo: forma passada."),
                    ("帰（かえ）ります", "Não-passado não combina com 「昨夜」."),
                    ("帰（かえ）っています", "Estado atual, não o fato de ontem."),
                ],
                "Marcador fechado pede passado.",
            ),
            _q(
                "ふだん朝（あさ）コーヒーを____。",
                "飲（の）みます",
                [
                    ("飲（の）みます", "「ふだん」marca hábito atual."),
                    ("飲（の）みました", "Passado encerraria o hábito."),
                    ("飲（の）んでいます", "Progressivo descreve agora, não a rotina."),
                ],
                "Hábito que continua válido.",
            ),
            _q(
                "電話（でんわ）して、それから____。",
                "出（で）ました",
                [
                    ("出（で）ました", "Sequência no passado: os dois verbos no passado."),
                    ("出（で）ます", "Não-passado quebra a sequência."),
                    ("出（で）てください", "Pedido, não relato de fato."),
                ],
                "Sequência de fatos no passado.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "その映画（えいが）を見（み）た____があります。",
                "こと",
                [
                    ("こと", "「〜たことがある」marca experiência."),
                    ("もの", "Não forma a expressão de experiência."),
                    ("とき", "「とき」marca ocasião, não experiência acumulada."),
                ],
                "Experiência acumulada, sem data fechada.",
            ),
            _q(
                "2019年（ねん）にそこへ____。",
                "行（い）きました",
                [
                    ("行（い）きました", "Ano fechado: passado simples."),
                    ("行（い）ったことがあります", "「ことがある」não combina com o ano explícito."),
                    ("行（い）きます", "Não-passado não combina com 2019."),
                ],
                "Marcador fechado pede passado.",
            ),
            _q(
                "5月（がつ）からここで働（はたら）いて____。",
                "います",
                [
                    ("います", "「〜ている」+ 「から」: ação ainda em curso."),
                    ("いました", "Passado encerraria o período."),
                    ("ください", "Pedido, não descrição do estado."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "それが遅（おく）れの理由（りゆう）____。",
                "かもしれません",
                [
                    ("かもしれません", "Possibilidade, não certeza."),
                    ("ましょう", "Convite, não hipótese."),
                    ("てください", "Pedido, não modalização."),
                ],
                "Grau de certeza menor.",
            ),
            _q(
                "もっと時間（じかん）が____、終わっていたでしょう。",
                "あったら",
                [
                    ("あったら", "「たら」forma a hipótese sobre o passado."),
                    ("あります", "Não-passado não forma o contrafactual."),
                    ("あってください", "Pedido, não condição."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "それは____より安全（あんぜん）な選択（せんたく）です。",
                "おそらく",
                [
                    ("おそらく", "Ressalva de probabilidade."),
                    ("たぶんに", "Forma inexistente; o advérbio é たぶん ou おそらく."),
                    ("きっとに", "「きっと」não leva に neste uso."),
                ],
                "Ressalva que não torna a afirmação categórica.",
            ),
        ],
    },
    "zh-CN": {
        BAND_BEGINNER: [
            _q(
                "你从____来？",
                "哪里",
                [
                    ("哪里", "「从哪里」pergunta a origem."),
                    ("什么", "「什么」não forma esta pergunta de lugar."),
                    ("谁", "「谁」pergunta a pessoa."),
                ],
                "Pergunta de origem.",
            ),
            _q(
                "你做____工作？",
                "什么",
                [
                    ("什么", "「什么工作」pergunta a ocupação."),
                    ("哪里", "「哪里」pergunta lugar."),
                    ("谁", "「谁」pergunta a pessoa."),
                ],
                "Pergunta de rotina.",
            ),
            _q(
                "我____学生。",
                "是",
                [
                    ("是", "「是」liga a identidade: 我是学生."),
                    ("在", "「在」marca lugar ou progressivo, não identidade."),
                    ("有", "「有」marca posse, não 'eu sou'."),
                ],
                "Identidade: 我是……",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "昨晚我很晚才____。",
                "回家了",
                [
                    ("回家了", "「了」+ 「昨晚」marca o fato concluído."),
                    ("回家", "Sem 「了」fica genérico, não o evento de ontem."),
                    ("在回家", "Progressivo descreve agora, não ontem."),
                ],
                "Marcador fechado pede ação concluída.",
            ),
            _q(
                "我通常早上____咖啡。",
                "喝",
                [
                    ("喝", "「通常」marca hábito atual, sem 「了」."),
                    ("喝了", "「了」encerraria um evento, não a rotina."),
                    ("在喝", "Progressivo descreve o momento, não o hábito."),
                ],
                "Hábito que continua válido.",
            ),
            _q(
                "他打了电话，然后____。",
                "离开了",
                [
                    ("离开了", "Sequência de fatos concluídos: os dois com 「了」."),
                    ("离开", "Sem 「了」não fecha o segundo fato."),
                    ("在离开", "Progressivo não fecha a sequência."),
                ],
                "Sequência de fatos no passado.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "我看____那部电影。",
                "过",
                [
                    ("过", "「过」marca experiência acumulada."),
                    ("了", "「了」marcaria um fato pontual."),
                    ("着", "「着」marca estado durativo."),
                ],
                "Experiência, sem momento fechado.",
            ),
            _q(
                "我2019年____那里。",
                "去了",
                [
                    ("去了", "Ano fechado: fato pontual com 「了」."),
                    ("去过", "「过」não combina com o ano explícito."),
                    ("去", "Sem marcação não fecha 2019."),
                ],
                "Marcador fechado pede fato pontual.",
            ),
            _q(
                "她从五月起一直在这里____。",
                "工作",
                [
                    ("工作", "「从……起一直」marca ação ainda em curso."),
                    ("工作了就停", "Encerraria o período; a frase diz que continua."),
                    ("工作过", "「过」marcaria experiência já encerrada."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "这____能解释延误。",
                "也许",
                [
                    ("也许", "Possibilidade, não certeza."),
                    ("必须得要", "Redundante e categórico demais."),
                    ("一定不要", "Negação, não hipótese."),
                ],
                "Modalização de possibilidade.",
            ),
            _q(
                "要是我有更多时间，____会做完。",
                "就",
                [
                    ("就", "Par 「要是…就…」."),
                    ("才", "「才」marca 'só então', não este par."),
                    ("还", "「还」marca 'ainda', não a condição."),
                ],
                "Hipótese: condição e resultado.",
            ),
            _q(
                "这____是更稳妥的选择。",
                "可以说",
                [
                    ("可以说", "Ressalva: defensável, não absoluto."),
                    ("说法", "Substantivo; a frase pede o encaixe verbal."),
                    ("说了", "Fato passado, não ressalva."),
                ],
                "Ressalva que preserva o argumento.",
            ),
        ],
    },
    "la": {
        BAND_BEGINNER: [
            _q(
                "____ vocaris?",
                "Quomodo",
                [
                    ("Quomodo", "'Quomodo vocaris?' pergunta o nome."),
                    ("Ubi", "'Ubi' pergunta lugar."),
                    ("Quis", "'Quis' pergunta 'quem', não o padrão do nome."),
                ],
                "Pergunta de identidade.",
            ),
            _q(
                "____ venis?",
                "Unde",
                [
                    ("Unde", "'Unde venis?' pergunta a origem."),
                    ("Quo", "'Quo' pergunta o destino."),
                    ("Cur", "'Cur' pergunta a causa."),
                ],
                "Pergunta de origem.",
            ),
            _q(
                "Ego ____ discipulus.",
                "sum",
                [
                    ("sum", "'Ego' pede 'sum'."),
                    ("es", "'Es' combina com tu."),
                    ("est", "'Est' combina com a terceira pessoa."),
                ],
                "Identidade: ego sum.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "Heri sero ____.",
                "redii",
                [
                    ("redii", "'Heri' fecha o tempo: perfeito."),
                    ("redeo", "Presente não combina com 'heri'."),
                    ("redibo", "Futuro aponta para depois, não para ontem."),
                ],
                "Marcador fechado pede perfeito.",
            ),
            _q(
                "Saepe mane ____.",
                "oro",
                [
                    ("oro", "'Saepe' com hábito atual: presente."),
                    ("oravi", "Perfeito encerraria o hábito."),
                    ("orabam", "Imperfeito descreve hábito passado."),
                ],
                "Hábito que continua válido.",
            ),
            _q(
                "Vocavit et deinde ____.",
                "discessit",
                [
                    ("discessit", "Sequência no perfeito: os dois verbos no passado."),
                    ("discedit", "Presente quebra a sequência."),
                    ("discedet", "Futuro não fecha o segundo fato."),
                ],
                "Sequência de fatos no passado.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "Romam ter ____.",
                "ivi",
                [
                    ("ivi", "Contagem de experiência sem data: perfeito de contagem."),
                    ("eo", "Presente não marca as três idas."),
                    ("ibo", "Futuro não descreve o que já ocorreu."),
                ],
                "Experiência acumulada, sem ano fechado.",
            ),
            _q(
                "Anno MMXIX illuc ____.",
                "veni",
                [
                    ("veni", "Ano fechado: perfeito."),
                    ("venio", "Presente não combina com o ano."),
                    ("veniam", "Subjuntivo/futuro não fecha o fato de 2019."),
                ],
                "Marcador fechado pede perfeito.",
            ),
            _q(
                "Ab mense Maio hic ____.",
                "laboro",
                [
                    ("laboro", "'Ab' + presente: a ação continua."),
                    ("laboravi", "Perfeito encerraria o período."),
                    ("laborabo", "Futuro não descreve o que já começou."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "Hoc moram ____ explicet.",
                "fortasse",
                [
                    ("fortasse", "Possibilidade, não certeza."),
                    ("certe non", "Negação categórica, não hipótese."),
                    ("necesse est", "Necessidade, não possibilidade."),
                ],
                "Modalização de possibilidade.",
            ),
            _q(
                "Si plus temporis ____, perfecissem.",
                "habuissem",
                [
                    ("habuissem", "Contrafactual passado: mais-que-perfeito do subjuntivo."),
                    ("habeo", "Presente do indicativo não forma a hipótese."),
                    ("habui", "Perfeito do indicativo marca fato, não irreal."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "Haec est, ____, tutior optio.",
                "ut videtur",
                [
                    ("ut videtur", "Ressalva: 'ao que parece', não fato absoluto."),
                    ("videt", "Verbo finito solto não cabe como ressalva."),
                    ("visum", "Supino/particípio não fecha esta ressalva."),
                ],
                "Ressalva que preserva o argumento.",
            ),
        ],
    },
    "la-classical": {
        BAND_BEGINNER: [
            _q(
                "____ vocāris?",
                "Quōmodo",
                [
                    ("Quōmodo", "'Quōmodo vocāris?' pergunta o nome."),
                    ("Ubi", "'Ubi' pergunta lugar."),
                    ("Quis", "'Quis' pergunta 'quem'."),
                ],
                "Pergunta de identidade na prosa clássica.",
            ),
            _q(
                "____ venīs?",
                "Unde",
                [
                    ("Unde", "'Unde venīs?' pergunta a origem."),
                    ("Quō", "'Quō' pergunta o destino."),
                    ("Cūr", "'Cūr' pergunta a causa."),
                ],
                "Pergunta de origem.",
            ),
            _q(
                "Ego ____ discipulus.",
                "sum",
                [
                    ("sum", "'Ego' pede 'sum'."),
                    ("es", "'Es' combina com tū."),
                    ("est", "'Est' combina com a terceira pessoa."),
                ],
                "Identidade: ego sum.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "Heri sērō domum ____.",
                "rediī",
                [
                    ("rediī", "'Herī' fecha o tempo: perfeito."),
                    ("redeō", "Presente não combina com 'herī'."),
                    ("redībō", "Futuro aponta para depois."),
                ],
                "Marcador fechado pede perfeito.",
            ),
            _q(
                "Saepe māne ____.",
                "legō",
                [
                    ("legō", "'Saepe' com hábito atual: presente."),
                    ("lēgī", "Perfeito encerraria o hábito."),
                    ("legēbam", "Imperfeito descreve hábito passado."),
                ],
                "Hábito que continua válido.",
            ),
            _q(
                "Vocāvit et deinde ____.",
                "discessit",
                [
                    ("discessit", "Sequência no perfeito."),
                    ("discēdit", "Presente quebra a sequência."),
                    ("discēdet", "Futuro não fecha o segundo fato."),
                ],
                "Sequência de fatos no passado.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "Rōmam ter ____.",
                "īvī",
                [
                    ("īvī", "Contagem de idas, sem ano fechado."),
                    ("eō", "Presente não marca as três idas."),
                    ("ībō", "Futuro não descreve o passado."),
                ],
                "Experiência acumulada.",
            ),
            _q(
                "Annō MMXIX illūc ____.",
                "vēnī",
                [
                    ("vēnī", "Ano fechado: perfeito."),
                    ("veniō", "Presente não combina com o ano."),
                    ("veniam", "Não fecha o fato de 2019."),
                ],
                "Marcador fechado pede perfeito.",
            ),
            _q(
                "Ab mēnse Māiō hīc ____.",
                "labōrō",
                [
                    ("labōrō", "'Ab' + presente: a ação continua."),
                    ("labōrāvī", "Perfeito encerraria o período."),
                    ("labōrābō", "Futuro não descreve o que já começou."),
                ],
                "Ação ainda em curso.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "Hoc moram ____ explicet.",
                "fortasse",
                [
                    ("fortasse", "Possibilidade, não certeza."),
                    ("certē nōn", "Negação categórica."),
                    ("necesse est", "Necessidade, não possibilidade."),
                ],
                "Modalização.",
            ),
            _q(
                "Sī plūs temporis ____, perfēcissem.",
                "habuissem",
                [
                    ("habuissem", "Contrafactual: mais-que-perfeito do subjuntivo."),
                    ("habeō", "Indicativo presente não forma a hipótese."),
                    ("habuī", "Perfeito do indicativo marca fato."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "Haec est, ____, tūtior optiō.",
                "ut vidētur",
                [
                    ("ut vidētur", "Ressalva: ao que parece."),
                    ("videt", "Verbo finito solto não cabe."),
                    ("vīsum", "Não fecha esta ressalva."),
                ],
                "Ressalva que preserva o argumento.",
            ),
        ],
    },
}


def extra_exercises(language_code: str, band: str) -> list[dict]:
    table = EXTRA.get(language_code) or {}
    return list(table.get(band) or [])
