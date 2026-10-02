<p align="center">
  <img src="assets/banner.png" alt="F.I.O. Lab: a Python OSINT lab for link analysis across phone numbers and Brazilian public records" width="860">
</p>

<p align="center">
  <a href="https://github.com/Ridd1kulusC0d3r/FIO/actions/workflows/testes.yml"><img alt="tests" src="https://github.com/Ridd1kulusC0d3r/FIO/actions/workflows/testes.yml/badge.svg"></a>
  <a href="https://colab.research.google.com/github/Ridd1kulusC0d3r/FIO/blob/main/colab/FIO_Lab_Colab.ipynb"><img alt="Open in Colab" src="https://colab.research.google.com/assets/colab-badge.svg"></a>
  <img alt="version 3.1.0" src="https://img.shields.io/badge/version-3.1.0-0B4F6C">
  <img alt="Python 3.10–3.14" src="https://img.shields.io/badge/python-3.10%E2%80%933.14-3776AB">
  <img alt="zero dependencies" src="https://img.shields.io/badge/dependencies-none-0E7C6B">
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-555"></a>
</p>

<p align="center"><b>English</b> · <a href="README.pt-BR.md">Português</a></p>

<p align="center"><strong>F.I.O. — <i>Fontes, Identificadores e Origens</i> (Sources, Identifiers and Origins)</strong><br>
Do these phone numbers belong to the same person, company or group? How confident are we?<br>And how often is that answer wrong?</p>

<p align="center">
  <img src="docs/img/demo.gif" alt="The F.I.O. workbench: open the demo case, explore the graph, review links, observations and the chain of custody" width="860">
</p>

---

## What it is

F.I.O. Lab cross-references **phone numbers, company registrations (CNPJ), partners, e-mails, domains and official gazettes** into a link graph in which **every edge carries the source that supports it**. It is pure Python (standard library only, including the web workbench) and runs on your machine or in Google Colab.

It is built for Brazilian public data: the national numbering plan, the Federal Revenue open-data CNPJ dump, municipal gazettes (Querido Diário), CEIS/CNEP sanctions, registro.br RDAP and more. The interface and documentation are in Brazilian Portuguese; the code, CLI and exports are stable and scriptable.

Three rules that are not negotiable:

| Rule | How it shows up in the code |
|---|---|
| **No scope, no collection.** | Every case needs a legal basis, a purpose and an expiry date. Scope is checked at every pivot; outside it, collectors refuse to run. |
| **No source, no link.** | An edge is born with at least one `Fonte` (source). Confidence follows the Admiralty scale, combines only **independent** sources and never reaches 100%. |
| **No evidence, no conclusion.** | Every conclusion in a report cites the graph edge behind it. Everything collected goes into a SHA-256 hash-chained ledger. |

> A link is a *documented co-occurrence between identifiers*, not proof of a relationship. F.I.O. says so in every report.

## Three ways to run it

| Way | For whom | How |
|---|---|---|
| **Google Colab** | try it with zero setup | click *Open in Colab* › *Runtime › Run all* (ephemeral session, nothing is mounted from Drive) |
| **Two clicks** | non-technical users, local machine | download the latest [Release](https://github.com/Ridd1kulusC0d3r/FIO/releases), unzip, open the launcher for your OS ([COMECE-AQUI.md](COMECE-AQUI.md)) |
| **Command line** | engineers | `pip install git+https://github.com/Ridd1kulusC0d3r/FIO` then `fio --help` |

```bash
fio demo --abrir         # fictional case, 100% offline, opens the workbench
fio lab bancada         # the web workbench at http://127.0.0.1:8765
```

Requires **Python 3.10+**. No `pip install` of third-party packages, ever.

## The workbench

<table>
  <tr>
    <td width="50%"><img src="docs/img/painel-claro.png" alt="Workbench dashboard, light theme"></td>
    <td width="50%"><img src="docs/img/grafo-detalhe.png" alt="Link graph with a detail panel for a phone number and its sources"></td>
  </tr>
  <tr>
    <td><sub><b>Dashboard.</b> Cases, one-click demo case, source health check.</sub></td>
    <td><sub><b>Graph.</b> Edge width and style follow confidence; clicking shows attributes, links and sources with hashes.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/img/observacoes.png" alt="Analytical observations with severity and a button to highlight them on the graph"></td>
    <td><img src="docs/img/grafo-escuro.png" alt="Link graph in dark theme"></td>
  </tr>
  <tr>
    <td><sub><b>Observations.</b> Patterns worth checking, with the analyzer that raised them. They are not accusations.</sub></td>
    <td><sub><b>Dark theme</b> and a responsive layout (works on a phone); no external fonts or scripts.</sub></td>
  </tr>
</table>

The server listens on loopback only, requires a per-session token (in the URL fragment, so it never reaches logs or `Referer`), checks the `Host` header against DNS rebinding and sends no CORS headers.

## How it works

```text
 targets ─► prepare ─► collect ───────────────► analyze ─► report
            plugins     ingest     nucleo        coherence    technical (HTML/MD/CSV)
            code hash   normalize  cnpj-reverso  reg. batch   expert report (CPP art. 158-B)
                        enrich     querido-diário line reuse  intelligence report
                                   crt.sh · wayback · rdap    intermediaries
                                   viacep · transparência     sanctions
                          │                  │
                          ▼                  ▼
                 SHA-256 ledger        graph (Admiralty per source)
                 + raw artifacts       ─► claims ─► manifest
```

See [ARQUITETURA.md](ARQUITETURA.md) for the full design (Portuguese).

## What's in 3.x

| | What it does | Why it matters |
|---|---|---|
| **Differential baseline** | Before trusting a response, queries a value that **cannot exist** and compares. A near-identical answer is discarded. | Kills the classic false hit: the source returns "200 OK" for anything. |
| **Contract canaries** | `fio/fontes.json` declares what each source must return. `fio diagnostico` separates *down* from *changed format*. | Tells you a collector broke before anyone reads an empty report. |
| **Registration batch** | Companies with different CNPJ roots opened within 30 days and tied by phone, e-mail, ZIP or partner. | Shell-company networks open in batches. So do accountants: the observation text explains how to tell them apart. |
| **Line reuse** | A phone declared by a closed company and by an active one. | Stops a recycled number from being read as a common operator. |
| **crt.sh and Wayback** | Sibling names from Certificate Transparency and a domain's first capture. | Real age and shared infrastructure, without touching the target. |
| **Boleto, PIX, CNH, CNS** | Payment-slip line (mod 10/11 checks, bank, amount, due date), random PIX keys, CNH and SUS card validation. | Extracts financial identifiers from free text without mistaking them for a CNPJ. |
| **Traceable claims** | `fio claims`: each conclusion points at the edge that supports it. | A conclusion with no evidence in the graph does not enter the report. |
| **SHA-256 manifest** | `fio manifesto`: a hash of every deliverable tied to the ledger. | Detects a changed file, a tampered manifest and a rewritten ledger. |
| **Calibration** | `fio lab calibrar`: declared confidence vs observed precision. | Measures whether "0.76" really means 76%. |
| **Ready-made CNPJ index** | `fio indice baixar --uf MG --pronto` downloads a compressed, lean index in **seconds** (SHA-256 checked, resumable) instead of building it from GBs of Revenue data. | The Revenue server often blocks cloud IPs; the ready index is hosted on GitHub, which Colab reaches. |
| **Fast, light search** | Network sources run in parallel; `--rapido` and `--orcamento` cap the work; ledger and graph hot paths fixed. | The offline pipeline went from 40 s to 3.8 s on a 60-group synthetic world. See [docs/guia/desempenho.md](docs/guia/desempenho.md). |
| **Colab-ready workbench** | The full UI works behind Colab's proxy and inside iframes with blocked storage. | Covered by an end-to-end test that simulates exactly that. |

Full list in the [CHANGELOG](CHANGELOG.md).

## How accurate is it?

Fictional worlds with ground truth and the traps that break real link analysis (accountant hubs, recycled numbers, straw owners, homonyms, **shell networks**…), always offline. Mean ± standard deviation over 10 worlds × 15 groups:

| Configuration | Precision | Recall | F1 |
|---|---|---|---|
| combined, threshold 0.2, no pruning | 0.441 ± 0.154 | 0.885 ± 0.068 | 0.575 ± 0.141 |
| combined, threshold 0.2, **with** intermediary pruning | 0.774 ± 0.184 | 0.714 ± 0.070 | 0.727 ± 0.115 |
| combined, **threshold 0.4** | **0.878 ± 0.058** | 0.714 ± 0.070 | **0.785 ± 0.052** |
| partner by name only (ablation) | 0.389 ± 0.146 | 0.885 ± 0.068 | 0.527 ± 0.145 |

And calibration, without make-up: confidence **ranks** correctly but is **coarse** (edges fall into three values) and **conservative** (the 0.3–0.4 bin is right 49% of the time; 0.7–0.8 is right 100% on synthetic data). Relative comparisons are what matter; validate on labeled real cases before quoting absolute numbers. Method and reading: [docs/guia/avaliacao.md](docs/guia/avaliacao.md) (Portuguese).

## Command line

```bash
# a case with legal basis, purpose and scope
fio caso novo --id CASE-2026-020 --titulo "..." --base-legal lgpd-7-vi \
  --finalidade "support an extrajudicial notice about a fraudulent charge" \
  --responsavel "Jane Doe" --escopo "+5531988887777" "example.com.br"

fio alvo --caso CASE-2026-020 --tipo telefone --valor "(31) 98888-7777"
fio lab pipeline --caso CASE-2026-020 --profundidade 2 --expandir-escopo \
  --relatorio technical.html --laudo expert-report.html
fio claims --caso CASE-2026-020                # conclusions and their evidence
fio relatorio --caso CASE-2026-020 --saida r.html --markdown r.md --manifesto
fio manifesto verificar --caso CASE-2026-020   # has anything changed since issue?
fio doc extrair minutes.txt                    # CPF, CNPJ, ZIP, plate, boleto, PIX key…
```

Command names are Portuguese; the complete, auto-generated reference is in [docs/guia/referencia-cli.md](docs/guia/referencia-cli.md).

## Sources

Each collector declares an Admiralty grade and its **reservation** (the known limit of the source), which goes into the report.

| Collector | Source | Mode | Grade |
|---|---|---|---|
| `nucleo` | national numbering plan (local table) | offline | A2 |
| `cnpj-reverso` | Federal Revenue CNPJ open data, local index | offline | A2 |
| `dados-abertos` | any open CSV/JSON/ZIP, indexed by *recipe* | offline | per recipe |
| `cnpj-api` | BrasilAPI (Revenue mirror) | network | B2 |
| `querido-diario` | municipal official gazettes | network | A3 |
| `viacep`, `rdap`, `transparencia` | ZIP/IBGE, registro.br, CEIS/CNEP sanctions | network | B2 / A2 / A1 |
| `crtsh`, `wayback` | Certificate Transparency, Internet Archive | network | B3 / B2 |
| `web`, `hibp` | public index (with baseline), Have I Been Pwned | network | C3 / B2 |

## Limits and responsible use

By construction — with no flag to turn it on — F.I.O. **refuses**: leaked databases, third-party credentials, interception, social engineering and messaging-platform enumeration. A full CPF found in a document enters the graph **masked only** (LGPD art. 6, III). Collection is passive: no collector ever touches the target. A link is documented co-occurrence, not proven relationship. Read [USO-RESPONSAVEL.md](USO-RESPONSAVEL.md) and [SECURITY.md](SECURITY.md) before the first real case.

## Documentation

The guides are in Brazilian Portuguese.

| | |
|---|---|
| [Guides index](docs/guia/README.md) | where to start, by goal |
| [Getting started](docs/guia/primeiros-passos.md) · [Concepts](docs/guia/conceitos.md) · [Reading results](docs/guia/interpretando-resultados.md) | the 30-minute path |
| [Use-case recipes](docs/guia/receitas-de-uso.md) | fraud lines, company groups, shell networks, domains, expert reports |
| [Colab](docs/guia/colab.md) · [Workbench](docs/guia/bancada.md) · [Configuration](docs/guia/configuracao.md) | running and setting it up |
| [CLI reference](docs/guia/referencia-cli.md) | auto-generated from the real parser |
| [ARQUITETURA.md](ARQUITETURA.md) · [CHANGELOG.md](CHANGELOG.md) · [CONTRIBUTING.md](CONTRIBUTING.md) | internals and history |

## Development

```bash
python -m unittest discover -s testes -v     # 139 tests; the E2E needs Playwright
python testes/fumaca.py                      # CLI smoke test
python testes/ao_vivo.py                     # live source contract (needs internet)
python tools/gerar_midia.py                  # regenerates docs/img/demo.gif
```

## Citation and license

MIT. To cite, use [CITATION.cff](CITATION.cff).
