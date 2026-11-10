<#
.SYNOPSIS
  Invólucro fino: chama atualizar.py (que roda em Windows, Linux e macOS) repassando os parâmetros.

.DESCRIPTION
  A geração mora em atualizar.py, ao lado deste arquivo: valida o modelo, exporta o JSON e regenera os documentos
  derivados, o leitor e o explorador. Este .ps1 existe para quem já o chama (o gancho do git, ver-arquitetura.ps1,
  sua própria rotina). Em qualquer sistema, o caminho direto é:  python scripts/atualizar.py

  Mapeamento dos parâmetros para as flags do atualizar.py:
    -Ferramentas  --ferramentas    -Python       --python        -Template     --template
    -Checkpoint   --checkpoint-env (o rótulo viaja por LODEMAP_CHECKPOINT, Unicode intacto)
    -ComSite      --com-site       -SemExtensoes --sem-extensoes -SemSite      --sem-site
    -Incremental  --incremental
  Só o que você passou é repassado; os padrões (STRUCTURIZR_FERRAMENTAS, LODEMAP_PYTHON, LODEMAP_TEMPLATE) valem no
  atualizar.py. O código de saída é o do atualizar.py.

.PARAMETER Ferramentas
  Pasta com cli\structurizr.bat e graphviz\. Padrão: $env:STRUCTURIZR_FERRAMENTAS ou $HOME\.structurizr.

.PARAMETER Python
  Executável do Python. Padrão: $env:LODEMAP_PYTHON ou "python".

.PARAMETER Template
  Pasta templates\structurizr da skill. Padrão: $env:LODEMAP_TEMPLATE ou $HOME\.claude\skills\lodemap\templates\structurizr.

.PARAMETER ComSite
  Exporta também o site estático do Structurizr em ..\site.

.PARAMETER SemExtensoes
  Não roda as extensões locais nesta geração.

.PARAMETER SemSite
  Mantido por compatibilidade (o gancho do git o passa); o site já fica de fora sem -ComSite.

.PARAMETER Incremental
  Sai sem regenerar se o lodemap_diff.py não achar mudança desde a última geração.

.PARAMETER Checkpoint
  Rótulo do checkpoint (por exemplo "merge feat/x"). Vai para o estado.json e para as extensões locais.
#>
param(
    [string]$Ferramentas,
    [string]$Python,
    [switch]$ComSite,
    [switch]$SemExtensoes,
    [switch]$SemSite,
    [switch]$Incremental,
    [string]$Checkpoint,
    [string]$Template
)

$py = Join-Path $PSScriptRoot "atualizar.py"
if (-not (Test-Path $py)) { Write-Error "Não achei $py."; exit 1 }
$exe = if ($PSBoundParameters.ContainsKey("Python")) { $Python } elseif ($env:LODEMAP_PYTHON) { $env:LODEMAP_PYTHON } else { "python" }

$a = @()
if ($PSBoundParameters.ContainsKey("Ferramentas")) { $a += @("--ferramentas", $Ferramentas) }
if ($PSBoundParameters.ContainsKey("Python")) { $a += @("--python", $Python) }
if ($PSBoundParameters.ContainsKey("Template")) { $a += @("--template", $Template) }
if ($ComSite) { $a += "--com-site" }
if ($SemExtensoes) { $a += "--sem-extensoes" }
if ($SemSite) { $a += "--sem-site" }
if ($Incremental) { $a += "--incremental" }

# O rótulo vai pelo ambiente (Unicode intacto, qualquer que seja a página de código ou o shell que chamou).
$antes = $env:LODEMAP_CHECKPOINT
if ($PSBoundParameters.ContainsKey("Checkpoint")) { $env:LODEMAP_CHECKPOINT = $Checkpoint; $a += "--checkpoint-env" }
try {
    & $exe $py @a
    $rc = $LASTEXITCODE
} finally {
    if ($null -eq $antes) { Remove-Item Env:\LODEMAP_CHECKPOINT -ErrorAction SilentlyContinue } else { $env:LODEMAP_CHECKPOINT = $antes }
}
exit $rc
