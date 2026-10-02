# Laudo, RELINT e plugins

## Laudo e RELINT

`fio laudo --modelo laudo|relint` gera um documento para quem vai **ler** o
trabalho numa peça: preâmbulo, quesitos, material, metodologia (ISO/IEC
27037, escala Admiralty, reprodutibilidade), exames, **cadeia de custódia
mapeada nas 10 etapas do art. 158-B do CPP**, respostas aos quesitos,
limitações e conclusão graduada. O texto declara que a aplicação dos arts.
158-A a 158-F a vestígio digital é analógica e nunca redige conclusão
categórica.

## Plugins

```bash
cp exemplos/plugin_exemplo.py ~/.fio/plugins/
fio lab plugins
```

Coletor: subclasse de `Coletor` com `@registrar`. Analisador: subclasse de
`Analisador` com `@registrar_analisador`. O SHA-256 de cada plugin entra em
todo experimento que o usou.
