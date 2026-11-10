<#
.SYNOPSIS
  Invólucro fino: chama ver_arquitetura.py (que roda em Windows, Linux e macOS) repassando os parâmetros.

.DESCRIPTION
  O explorador, o leitor e o Structurizr Lite (opcional) são abertos pelo ver_arquitetura.py, ao lado deste arquivo.
  Este .ps1 existe para quem já o chama. Em qualquer sistema, o caminho direto é:  python scripts/ver_arquitetura.py

  Mapeamento dos parâmetros para as flags do ver_arquitetura.py:
    -Abrir        --abrir        (Explorador, Leitor, Lite ou Ambos)      -ComLite   --com-lite
    -Porta        --porta        -PortaExplorador --porta-explorador      -SemNavegador --sem-navegador
    -Ferramentas  --ferramentas  -Python          --python
  Só o que você passou é repassado; os padrões (STRUCTURIZR_FERRAMENTAS, LODEMAP_PYTHON e as portas do
  lodemap.json) valem no ver_arquitetura.py. O código de saída é o do ver_arquitetura.py.

.PARAMETER Abrir
  Explorador (padrão), Leitor, Lite (só o Lite) ou Ambos (explorador e Lite; o mesmo que -ComLite).

.PARAMETER ComLite
  Sobe e abre também o Structurizr Lite.

.PARAMETER Ferramentas
  Pasta com structurizr-lite.war e graphviz\. Padrão: $env:STRUCTURIZR_FERRAMENTAS ou $HOME\.structurizr.

.PARAMETER Porta
  Porta do Lite. Padrão: a do campo "lite" do lodemap.json (8790 se faltar).

.PARAMETER PortaExplorador
  Porta do servidor do explorador e do leitor. Padrão: a do campo "explorador" do lodemap.json (8791 se faltar).

.PARAMETER Python
  Executável do Python. Padrão: $env:LODEMAP_PYTHON ou "python".

.PARAMETER SemNavegador
  Sobe os servidores e não abre o navegador (útil para conferir por script).
#>
param(
    [string]$Ferramentas,
    [int]$Porta = 0,
    [int]$PortaExplorador = 0,
    [string]$Python,
    [ValidateSet("Explorador", "Leitor", "Lite", "Ambos")]
    [string]$Abrir = "Explorador",
    [switch]$ComLite,
    [switch]$SemNavegador
)

$py = Join-Path $PSScriptRoot "ver_arquitetura.py"
if (-not (Test-Path $py)) { Write-Error "Não achei $py."; exit 1 }
$exe = if ($PSBoundParameters.ContainsKey("Python")) { $Python } elseif ($env:LODEMAP_PYTHON) { $env:LODEMAP_PYTHON } else { "python" }

$a = @("--abrir", $Abrir.ToLower())
if ($PSBoundParameters.ContainsKey("Ferramentas")) { $a += @("--ferramentas", $Ferramentas) }
if ($PSBoundParameters.ContainsKey("Python")) { $a += @("--python", $Python) }
if ($Porta -ne 0) { $a += @("--porta", "$Porta") }
if ($PortaExplorador -ne 0) { $a += @("--porta-explorador", "$PortaExplorador") }
if ($ComLite) { $a += "--com-lite" }
if ($SemNavegador) { $a += "--sem-navegador" }

& $exe $py @a
exit $LASTEXITCODE
