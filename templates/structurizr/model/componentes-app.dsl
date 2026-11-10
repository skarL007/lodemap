    // Componentes por área, dentro de grupos. Cada um:
    //   - tags: <Status>,Area<Nome>[,Dados|Gate|Privacidade|Barramento|WebBrowser|Janela|Modelo]
    //   - properties: status (texto), area, codigo (caminhos), e o que houver (observabilidade, equipe, spec, nota, ramo)
    // Regra do codigo: caminhos separados por vírgula; nome sem barra herda a pasta do anterior;
    // parênteses são comentário; caminho terminado em "/" cobre a pasta.
    group "Núcleo" {
        appEntrada = component "Ponto de entrada" "Troque pelo módulo real que inicia a aplicação." "Python" "Pronto,AreaNucleo" {
            properties {
                "status" "Pronto"
                "area" "AreaNucleo"
                "codigo" "{{RAIZ_CODIGO}}/"
            }
        }
    }
