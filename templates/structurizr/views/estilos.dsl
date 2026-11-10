            element "Element" {
                color #f4f7fb
                fontSize 22
                strokeWidth 3
            }
            element "Person" {
                shape Person
                background #1d4f91
            }
            element "Software System" {
                shape RoundedBox
                background #2b3a52
            }
            element "Container" {
                width 400
                height 220
                shape RoundedBox
                background #2b3a52
            }
            element "Component" {
                width 340
                height 140
                fontSize 26
                description false
                metadata false
                shape RoundedBox
                background #2b3a52
            }
            element "Dados" {
                shape Cylinder
            }
            element "Gate" {
                shape Hexagon
            }
            element "Privacidade" {
                strokeWidth 6
                stroke #ffd166
            }
            element "Modelo" {
                shape Robot
            }
            element "WebBrowser" {
                shape WebBrowser
            }
            element "Janela" {
                shape Window
            }
            element "Barramento" {
                shape Pipe
            }
            element "Externo" {
                border dashed
                stroke #f0883e
            }
            element "Nuvem" {
                border dashed
                stroke #f0883e
            }
            element "Pronto" {
                background #1f7a4d
            }
            element "EmAndamento" {
                background #b7791f
            }
            element "Aguardando" {
                background #6b46c1
            }
            element "Planejado" {
                background #3b4a63
                border dashed
                stroke #94a3b8
            }
            element "ForaDoFoco" {
                background #4a4f57
                opacity 70
            }
            element "Group" {
                color #9fb3c8
                stroke #4b5b73
            }
            relationship "Relationship" {
                color #9fb3c8
                thickness 2
                fontSize 20
            }
            relationship "Planejado" {
                color #f0883e
                dashed true
            }
            relationship "Aguardando" {
                color #b794f4
                dashed true
            }
            relationship "EmAndamento" {
                color #f6c453
                dashed true
            }
            relationship "Gate" {
                color #ffd166
            }
