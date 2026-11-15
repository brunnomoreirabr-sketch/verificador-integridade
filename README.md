# Verificador de Integridade

Cria um inventário SHA-256 de uma pasta e compara esse inventário com o estado atual. Identifica arquivos adicionados, alterados, removidos e arquivos que não puderam ser verificados.

## Executar

Requer Python 3.10 ou superior, sem dependências externas.

```bash
git clone https://github.com/brunnomoreirabr-sketch/verificador-integridade.git
cd verificador-integridade
python -m integridade.cli criar exemplos/arquivos --saida inventario.json
python -m integridade.cli verificar exemplos/arquivos --inventario inventario.json --saida relatorio.json
```

No Linux/macOS, use `python3` quando necessário. Altere `exemplos/arquivos/anotacoes.txt` e execute novamente a verificação: o arquivo deve aparecer em `alterados`.

Guarde o inventário e os relatórios **fora da pasta verificada**. O programa recusa caminhos dentro dela e não sobrescreve um inventário existente. Para uma nova referência, escolha outro nome.

## Comportamento

- O hash é calculado em blocos de 1 MiB, sem carregar cada arquivo inteiro na memória.
- O inventário usa caminhos relativos, tamanho em bytes e hash SHA-256.
- Alterações no conteúdo são detectadas mesmo que o tamanho seja mantido.
- Links simbólicos e arquivos especiais são ignorados e listados no resultado.
- Arquivos modificados durante a leitura geram erro; não são considerados íntegros.
- Erros de acesso resultam em verificação incompleta. Um arquivo inacessível não é classificado como removido.
- A criação do inventário é recusada se houver erros de leitura. Um inventário parcial não vira referência silenciosamente.

O programa não modifica o conteúdo da pasta. Se um arquivo regular for substituído por um link simbólico, ele deixa de fazer parte dos arquivos regulares e aparece como removido; o link é listado entre os ignorados.

## Resultados e códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Inventário criado ou verificação concluída sem diferenças. |
| `1` | Diferenças encontradas. |
| `2` | Erro de execução ou verificação incompleta. |

Um inventário confiável precisa ser guardado separadamente: alterar os arquivos e o próprio inventário pode esconder mudanças. Esta ferramenta compara integridade; não substitui antivírus, assinatura digital ou backup. A comparação também não garante uma visão instantânea de uma pasta que continua sendo modificada durante a execução.

## Testes

```bash
python -m unittest discover -s tests -v
```

A suíte cobre mudanças com o mesmo tamanho, adição, remoção, links simbólicos, erros de acesso, validação do inventário e códigos de saída da CLI.

## Organização

- `integridade/core.py`: leitura, hashing, validação e comparação.
- `integridade/cli.py`: comandos `criar` e `verificar`.
- `exemplos/arquivos/`: arquivos fictícios para a demonstração.
- `tests/`: testes automatizados.

Licença [MIT](LICENSE).
