            // Um container por processo ou banco. Componentes em model/componentes-<container>.dsl.
            app = container "Aplicação" "Processo principal. Troque pela descrição real." "Python" "Pronto,AreaApp" {
                properties {
                    "status" "Pronto"
                    "codigo" "{{RAIZ_CODIGO}}/"
                }
                !include componentes-app.dsl
            }

            // Exemplo de container de dados (cilindro):
            // banco = container "Banco" "O que guarda." "SQLite" "Dados,Pronto" {
            //     properties {
            //         "status" "Pronto"
            //     }
            // }
