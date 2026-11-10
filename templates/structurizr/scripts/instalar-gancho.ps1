<#
.SYNOPSIS
  Invólucro fino: chama instalar_gancho.py (que roda em Windows, Linux e macOS) repassando os parâmetros.

.DESCRIPTION
  A instalação (opt-in) dos ganchos post-commit e post-merge mora no instalar_gancho.py, ao lado deste arquivo. Este
  .ps1 existe para quem já o chama. Em qualquer sistema, o caminho direto é:  python scripts/instalar_gancho.py

  Mapeamento dos parâmetros para as flags do instalar_gancho.py:
    -Python  --python    -Ferramentas  --ferramentas    -Remover  --remover    -Forcar  --forcar
  Só o que você passou é repassado. O código de saída é o do instalar_gancho.py. Gancho que já existe e não é da
  lodemap não é sobrescrito sem -Forcar; o log de cada atualização fica em .lodemap\ultimo-atualizar.log.

.PARAMETER Python
  Executável do Python que o gancho usa. Padrão: o "python" do PATH.

.PARAMETER Ferramentas
  Pasta do Structurizr CLI que o gancho passa ao atualizar.py (o gancho roda sem as variáveis da sua sessão).
  Padrão: $env:STRUCTURIZR_FERRAMENTAS ou $HOME\.structurizr.

.PARAMETER Remover
  Tira os ganchos instalados por este script (e só eles).

.PARAMETER Forcar
  Sobrescreve um gancho que já existe e não é deste script.
#>
param(
    [string]$Python,
    [string]$Ferramentas,
    [switch]$Remover,
    [switch]$Forcar
)

$py = Join-Path $PSScriptRoot "instalar_gancho.py"
if (-not (Test-Path $py)) { Write-Error "Não achei $py."; exit 1 }
$exe = if ($PSBoundParameters.ContainsKey("Python")) { $Python } else { "python" }

$a = @()
if ($PSBoundParameters.ContainsKey("Python")) { $a += @("--python", $Python) }
if ($PSBoundParameters.ContainsKey("Ferramentas")) { $a += @("--ferramentas", $Ferramentas) }
if ($Remover) { $a += "--remover" }
if ($Forcar) { $a += "--forcar" }

& $exe $py @a
exit $LASTEXITCODE
